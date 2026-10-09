"""
Đánh giá tầng ANSWER trên mẫu 150 câu lấy từ bộ 1000 câu (E:/NHÁP 2/tea_chatbot_qa_test_1000.jsonl).

Khác với backend/evaluation/answer_eval.py (chấm trên rag/evaluation/eval_set.json, không có
ground-truth answer), script này tận dụng `expected_answer` + `answer_key_points` có sẵn trong bộ
1000 câu để đo thêm 2 chỉ số mới:
  - Answer Correctness (1-5): câu trả lời có đúng so với đáp án chuẩn không (khác Faithfulness:
    phát hiện case retrieval lấy nhầm tài liệu nhưng LLM vẫn "bám" đúng ngữ cảnh sai đó).
  - Key point coverage: % đầu việc/ý (answer_key_points) được câu trả lời nêu tới — Completeness đo
    theo checklist cụ thể thay vì ước lượng chung chung 1-5.

Cùng lúc vẫn tính Faithfulness, Relevance như answer_eval.py để nhất quán phương pháp.

Với câu grading_mode="abstain_no_data" (24 câu, thuộc Tea_Regions_Project_Config — nguồn KHÔNG
được ingest vào ChromaDB): không gọi model chấm, chỉ kiểm tra chatbot có từ chối đúng và không tự
bịa số liệu (area_ha/altitude_m) hay không — đây là chỉ số An toàn/Abstention.

Với grading_mode="exact_value" (region_fact/coordinate/boolean, không nằm trong RAG index): cũng
không gọi model chấm — chỉ ghi nhận refused/not để báo cáo mức độ phủ (những câu này kỳ vọng bị từ
chối vì dữ liệu không thuộc phạm vi RAG, xem README của bộ dữ liệu).

Chạy: python -m backend.evaluation.qa1000_answer_eval --limit 150 --report docs/QA1000_ANSWER_RESULTS.md
"""
import argparse
import asyncio
import json
import re
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from openai import AsyncOpenAI

from backend.config import settings
from backend.evaluation.answer_eval import (
    _with_retry,
    copy_ratio,
    extract_numbers,
    generate_answer,
    has_style_noise,
    is_refusal,
    is_structured,
    parse_judge_json,
    unsupported_numbers,
)
from backend.services.assistant_service import get_default_retriever

DATASET_PATH = Path(r"E:\NHÁP 2\tea_chatbot_qa_test_1000.jsonl")
RUNS_DIR = Path(__file__).resolve().parent / "runs"
RETRIEVAL_TOP_K = 3

GENERATOR_MODEL = "openai/gpt-oss-120b"  # model đang dùng thật trong sản phẩm
JUDGE_MODEL = "qwen/qwen3.8-27b"  # khác model sinh, giữ đúng nguyên tắc answer_eval.py

# Phân bổ mẫu 150 câu: 24 câu abstain_no_data lấy hết (rẻ, đo an toàn quan trọng nhất);
# 126 câu còn lại phân theo tỉ lệ kích thước từng question_type trong 976 câu còn lại
# (đã làm tròn để tổng đúng 126).
BUCKET_QUOTA = {
    "direct_grounded": 21,
    "paraphrase": 21,
    "source_constrained": 21,
    "domain_question": 21,
    "completeness": 21,
    "numeric_extraction": 9,
    "region_fact": 3,
    "region_coordinate": 3,
    "region_boolean": 3,
    "source_caveat": 3,
}

JUDGE_PROMPT_V2 = """Bạn là người chấm chất lượng câu trả lời của một chatbot hỏi đáp về cây chè.

CÂU HỎI:
{question}

NGỮ CẢNH CHATBOT ĐÃ DÙNG (RAG retrieval, có thể sai hoặc thiếu):
{context}

ĐÁP ÁN CHUẨN (viết từ tài liệu gốc, KHÔNG phải ngữ cảnh chatbot dùng):
{expected_answer}

CÁC Ý CHÍNH CẦN CÓ (answer_key_points):
{key_points}

CÂU TRẢ LỜI CỦA CHATBOT:
{answer}

Làm các việc sau, CHỈ dựa vào NGỮ CẢNH để chấm supported (không dùng kiến thức ngoài):
1. Tách câu trả lời chatbot thành các mệnh đề độc lập (bỏ lời chào, lời khuyên chung). Với mỗi mệnh đề,
   "supported": true nếu NGỮ CẢNH xác nhận, false nếu ngữ cảnh không nói/nói khác.
2. "correctness" (1-5): so với ĐÁP ÁN CHUẨN (không phải ngữ cảnh), câu trả lời chatbot đúng nội dung tới mức nào.
   5 = đúng hoàn toàn cùng nội dung với đáp án chuẩn; 1 = sai hoặc trái ngược đáp án chuẩn.
3. "key_points_covered": với mỗi ý trong CÁC Ý CHÍNH CẦN CÓ, true nếu câu trả lời chatbot có nêu (dù diễn đạt khác), false nếu bỏ sót.
   Trả về mảng boolean cùng thứ tự với danh sách ý chính đưa vào.
4. "relevance" (1-5): câu trả lời có đúng trọng tâm câu hỏi không.

Chỉ trả JSON, đúng dạng:
{{"claims": [{{"claim": "...", "supported": true}}], "correctness": 4, "key_points_covered": [true, false], "relevance": 5, "comment": "..."}}"""


def load_dataset() -> List[Dict[str, Any]]:
    return [json.loads(l) for l in DATASET_PATH.open(encoding="utf-8")]


def build_sample() -> List[Dict[str, Any]]:
    rows = load_dataset()
    abstain = [r for r in rows if r["grading_mode"] == "abstain_no_data"]
    assert len(abstain) == 24, f"kỳ vọng 24 câu abstain_no_data, thấy {len(abstain)}"

    sample = list(abstain)
    for qtype, quota in BUCKET_QUOTA.items():
        bucket = sorted((r for r in rows if r["question_type"] == qtype), key=lambda r: r["id"])
        step = max(1, len(bucket) // quota)
        sample.extend(bucket[::step][:quota])

    assert len(sample) == 150, f"kỳ vọng 150 câu, có {len(sample)}"
    return sample


def faithfulness(claims: List[Dict[str, Any]]) -> Optional[float]:
    if not claims:
        return None
    return sum(1 for c in claims if c.get("supported") is True) / len(claims)


def mean(values: List[float]) -> Optional[float]:
    values = [v for v in values if v is not None]
    return statistics.fmean(values) if values else None


async def judge_v2(question: str, context: str, expected_answer: str, key_points: List[str], answer: str) -> Optional[Dict[str, Any]]:
    client = AsyncOpenAI(api_key=settings.GROQ_API_KEY, base_url=settings.GROQ_BASE_URL)
    prompt = JUDGE_PROMPT_V2.format(
        question=question,
        context=context[: settings.MAX_CONTEXT_CHARS] or "(không có — chatbot đã từ chối/không truy xuất được)",
        expected_answer=expected_answer,
        key_points="\n".join(f"- {p}" for p in key_points),
        answer=answer,
    )

    async def call() -> str:
        res = await client.chat.completions.create(
            model=JUDGE_MODEL, messages=[{"role": "user", "content": prompt}], temperature=0, max_tokens=3000,
        )
        return res.choices[0].message.content or ""

    raw = await _with_retry(call)
    parsed = parse_judge_json(raw)
    if parsed is None:
        return None
    claims = parsed["claims"]
    covered = parsed.get("key_points_covered") or []
    n_kp = len(key_points)
    coverage = (sum(1 for c in covered if c is True) / n_kp) if n_kp and len(covered) == n_kp else None
    return {
        "claims": claims,
        "faithfulness": faithfulness(claims),
        "correctness": parsed.get("correctness"),
        "relevance": parsed.get("relevance"),
        "key_points_covered": covered,
        "key_point_coverage": coverage,
        "comment": parsed.get("comment", ""),
    }


def check_abstain_violation(answer: str, negative_constraints: str) -> bool:
    """True nếu câu trả lời có vẻ đã tự bịa số liệu dù đáng lẽ phải từ chối (vi phạm negative_constraints)."""
    if is_refusal(answer):
        return False
    # Có số liệu cụ thể trong câu trả lời trong khi lẽ ra phải nói "không có dữ liệu" -> nghi vi phạm
    return len(extract_numbers(answer)) > 0


async def evaluate(sample: List[Dict[str, Any]], pause_s: float) -> List[Dict[str, Any]]:
    retriever = get_default_retriever()
    records: List[Dict[str, Any]] = []
    for i, row in enumerate(sample, 1):
        question = row["question"]
        started = time.time()
        result = retriever.retrieve(question, top_k=RETRIEVAL_TOP_K)
        context = result["context_text"] if result["is_relevant"] else ""
        key_points = row.get("answer_key_points") or []
        if isinstance(key_points, str):
            try:
                key_points = json.loads(key_points)
            except json.JSONDecodeError:
                key_points = [key_points]

        record: Dict[str, Any] = {
            "id": row["id"], "question": question, "question_type": row["question_type"],
            "difficulty": row["difficulty"], "grading_mode": row["grading_mode"],
            "dataset": row["dataset"], "source_chunk_id": row.get("source_chunk_id"),
            "gate_relevant": result["is_relevant"], "answer": None, "refused": False,
            "latency_s": None, "unsupported_numbers": [], "judge": None, "judge_error": None,
            "abstain_violation": None,
        }
        try:
            record["answer"] = (
                await generate_answer(GENERATOR_MODEL, question, context)
                if result["is_relevant"] else
                "Hiện tại cơ sở tri thức chưa tìm thấy nguồn thông tin đủ phù hợp để giải đáp chính xác câu hỏi này."
            )
            record["latency_s"] = round(time.time() - started, 2)
            record["refused"] = is_refusal(record["answer"])
            record["words"] = len(record["answer"].split())
            record["structured"] = is_structured(record["answer"])
            record["style_noise"] = has_style_noise(record["answer"])
            record["copy_ratio"] = copy_ratio(record["answer"], context) if context else None

            if row["grading_mode"] == "abstain_no_data":
                record["abstain_violation"] = check_abstain_violation(record["answer"], row.get("negative_constraints", ""))
            elif row["grading_mode"] == "exact_value":
                record["unsupported_numbers"] = unsupported_numbers(record["answer"], context, question) if context else []
            else:  # semantic_factual
                record["unsupported_numbers"] = unsupported_numbers(record["answer"], context, question) if context else []
                if not record["refused"] and result["is_relevant"]:
                    try:
                        record["judge"] = await judge_v2(question, context, row["expected_answer"], key_points, record["answer"])
                        if record["judge"] is None:
                            record["judge_error"] = "không đọc được JSON của model chấm"
                    except Exception as err:
                        record["judge_error"] = f"{type(err).__name__}: {err}"[:200]
        except Exception as err:
            record["answer"] = f"[LỖI SINH CÂU TRẢ LỜI] {type(err).__name__}: {err}"[:300]

        records.append(record)
        j = record["judge"]
        print(f"  [{i}/{len(sample)}] {row['id']} ({row['question_type']}) refused={record['refused']} "
              f"correctness={j['correctness'] if j else '—'}", flush=True)
        await asyncio.sleep(pause_s)
    return records


def summarize(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    abstain = [r for r in records if r["grading_mode"] == "abstain_no_data"]
    exact = [r for r in records if r["grading_mode"] == "exact_value"]
    semantic = [r for r in records if r["grading_mode"] == "semantic_factual"]
    judged = [r for r in semantic if r.get("judge")]
    return {
        "n_total": len(records),
        "abstain": {
            "n": len(abstain),
            "correctly_abstained": sum(1 for r in abstain if r["refused"] or not r["gate_relevant"]),
            "violations_bịa_số": sum(1 for r in abstain if r["abstain_violation"]),
        },
        "exact_value_out_of_rag_scope": {
            "n": len(exact),
            "refused_or_not_relevant": sum(1 for r in exact if r["refused"] or not r["gate_relevant"]),
            "note": "Nguồn Tea_Regions_Project_Config không được ingest vào RAG; kỳ vọng từ chối vì ngoài phạm vi RAG hiện tại.",
        },
        "semantic_factual": {
            "n": len(semantic),
            "wrongly_refused": sum(1 for r in semantic if r["refused"] or not r["gate_relevant"]),
            "n_judged": len(judged),
            "faithfulness": mean([r["judge"]["faithfulness"] for r in judged]),
            "correctness": mean([r["judge"]["correctness"] for r in judged if isinstance(r["judge"].get("correctness"), (int, float))]),
            "relevance": mean([r["judge"]["relevance"] for r in judged if isinstance(r["judge"].get("relevance"), (int, float))]),
            "key_point_coverage": mean([r["judge"]["key_point_coverage"] for r in judged]),
            "answers_with_unsupported_numbers": sum(1 for r in semantic if r["unsupported_numbers"]),
            "judge_failures": sum(1 for r in semantic if r.get("judge_error")),
        },
        "avg_latency_s": mean([r["latency_s"] for r in records if r["latency_s"] is not None and r["gate_relevant"]]),
    }


def fmt(v: Optional[float], d: int = 3) -> str:
    return "—" if v is None else f"{v:.{d}f}"


def render_report(records: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
    lines = [
        "# Kết quả đánh giá Answer trên mẫu 150 câu (bộ 1000 câu)",
        "",
        f"Chạy lúc {datetime.now():%d/%m/%Y %H:%M}. Model sinh: `{GENERATOR_MODEL}` (đang dùng thật trong sản phẩm). "
        f"Model chấm: `{JUDGE_MODEL}` (khác model sinh). Nguồn mẫu: `{DATASET_PATH}`.",
        "",
        "## 1. An toàn / Abstention (24 câu `abstain_no_data`, dữ liệu vùng chè không có sẵn)",
        "",
        f"| N | Từ chối đúng | Vi phạm (tự bịa số liệu) |",
        f"|---|---|---|",
        f"| {summary['abstain']['n']} | {summary['abstain']['correctly_abstained']} | {summary['abstain']['violations_bịa_số']} |",
        "",
        "## 2. Câu hỏi ngoài phạm vi RAG hiện tại (36 câu region_fact/coordinate/boolean)",
        "",
        summary["exact_value_out_of_rag_scope"]["note"],
        "",
        f"| N | Từ chối / không liên quan |",
        f"|---|---|",
        f"| {summary['exact_value_out_of_rag_scope']['n']} | {summary['exact_value_out_of_rag_scope']['refused_or_not_relevant']} |",
        "",
        "## 3. Chất lượng câu trả lời (semantic_factual, có ground-truth)",
        "",
        "| N | Từ chối nhầm | Đã chấm | Faithfulness | **Answer Correctness (1-5)** | Relevance (1-5) | **Key point coverage** | Số liệu không căn cứ |",
        "|---|---|---|---|---|---|---|---|",
        f"| {summary['semantic_factual']['n']} | {summary['semantic_factual']['wrongly_refused']} | "
        f"{summary['semantic_factual']['n_judged']} | {fmt(summary['semantic_factual']['faithfulness'])} | "
        f"{fmt(summary['semantic_factual']['correctness'], 2)} | {fmt(summary['semantic_factual']['relevance'], 2)} | "
        f"{fmt(summary['semantic_factual']['key_point_coverage'])} | {summary['semantic_factual']['answers_with_unsupported_numbers']} |",
        "",
        f"Độ trễ trung bình (câu có gọi LLM): {fmt(summary['avg_latency_s'], 2)}s",
        "",
        "## Theo question_type (semantic_factual)",
        "",
        "| question_type | N | Correctness | Faithfulness | Key point coverage |",
        "|---|---|---|---|---|",
    ]
    semantic = [r for r in records if r["grading_mode"] == "semantic_factual" and r.get("judge")]
    for qtype in sorted(set(r["question_type"] for r in semantic)):
        rs = [r for r in semantic if r["question_type"] == qtype]
        lines.append(
            f"| {qtype} | {len(rs)} | {fmt(mean([r['judge']['correctness'] for r in rs]), 2)} | "
            f"{fmt(mean([r['judge']['faithfulness'] for r in rs]))} | {fmt(mean([r['judge']['key_point_coverage'] for r in rs]))} |"
        )
    return "\n".join(lines) + "\n"


async def run(limit: int, pause_s: float, report: Optional[str]) -> None:
    sample = build_sample()[:limit] if limit < 150 else build_sample()
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Mẫu: {len(sample)} câu", flush=True)
    records = await evaluate(sample, pause_s)
    summary = summarize(records)
    (RUNS_DIR / f"qa1000_answer_eval_{datetime.now():%Y%m%d_%H%M%S}.json").write_text(
        json.dumps({"summary": summary, "records": records}, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    text = render_report(records, summary)
    print(text)
    if report:
        Path(report).write_text(text, encoding="utf-8")
        print(f"Đã ghi {report}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=150)
    parser.add_argument("--pause", type=float, default=1.0)
    parser.add_argument("--report")
    args = parser.parse_args()
    asyncio.run(run(args.limit, args.pause, args.report))


if __name__ == "__main__":
    main()
