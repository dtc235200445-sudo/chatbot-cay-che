"""
Đánh giá chất lượng câu trả lời của chatbot (khác với rag/evaluation chỉ đo truy xuất).

Hai lớp chỉ số:
  1. Xác định (không dùng LLM chấm):
       - từ chối đúng: câu ngoài phạm vi phải bị từ chối; câu trong phạm vi không được từ chối nhầm;
       - số liệu có căn cứ: mọi con số trong câu trả lời phải có trong ngữ cảnh hoặc câu hỏi.
  2. LLM chấm (model chấm KHÁC model sinh để tránh thiên vị câu trả lời của chính nó):
       - độ bám nguồn: tỉ lệ mệnh đề trong câu trả lời được ngữ cảnh chứng minh;
       - trả lời đúng câu hỏi (1–5) và đầy đủ so với thông tin có trong ngữ cảnh (1–5).

Chạy:  python -m backend.evaluation.answer_eval --limit 24
Mọi câu trả lời, mệnh đề bị chấm "không có căn cứ" và nhận xét của model chấm đều được lưu để người kiểm tra lại.
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
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from fastapi import HTTPException
from openai import AsyncOpenAI

from backend.config import settings
from backend.services import llm_service
from backend.services.assistant_service import (
    LLM_REFUSAL_MARKER,
    LLM_REFUSAL_MAX_CHARS,
    NO_KNOWLEDGE_ANSWER,
    get_default_retriever,
)
from rag.evaluation.run_eval import load_eval_set

RUNS_DIR = Path(__file__).resolve().parent / "runs"
RETRIEVAL_TOP_K = 3

# (model sinh, model chấm): model chấm luôn khác model sinh
DEFAULT_PAIRS: List[Tuple[str, str]] = [
    ("openai/gpt-oss-120b", "qwen/qwen3.8-27b"),
    ("openai/gpt-oss-20b", "qwen/qwen3.8-27b"),
    ("qwen/qwen3.8-27b", "openai/gpt-oss-120b"),
]

JUDGE_PROMPT = """Bạn là người chấm chất lượng câu trả lời của một chatbot hỏi đáp về cây chè.
Chỉ dựa vào NGỮ CẢNH được cung cấp; KHÔNG dùng kiến thức bên ngoài để quyết định một mệnh đề đúng hay sai.

CÂU HỎI:
{question}

NGỮ CẢNH (các đoạn tài liệu chatbot được phép dùng):
{context}

CÂU TRẢ LỜI CỦA CHATBOT:
{answer}

Hãy làm các việc sau:
1. Tách câu trả lời thành các mệnh đề thông tin độc lập (bỏ qua câu dẫn, lời chào, lời khuyên chung chung và phần trích nguồn).
2. Với mỗi mệnh đề, xác định "supported": true nếu NGỮ CẢNH nói rõ điều đó (hoặc diễn đạt lại đúng nghĩa); false nếu ngữ cảnh không nói,
   nói khác, hoặc chatbot tự thêm mục đích/nguyên nhân/giải thích mà ngữ cảnh không nêu.
3. "relevance" (1-5): câu trả lời có trả lời đúng câu hỏi không (5 = trả lời trực tiếp và đúng trọng tâm, 1 = lạc đề).
4. "completeness" (1-5): so với thông tin liên quan CÓ TRONG NGỮ CẢNH, câu trả lời đã nêu đủ chưa (5 = đủ ý chính, 1 = bỏ sót gần hết).

Chỉ trả về JSON, không giải thích thêm, đúng dạng:
{{"claims": [{{"claim": "...", "supported": true}}], "relevance": 4, "completeness": 3, "comment": "nhận xét ngắn"}}"""


# ---------------------------------------------------------------- hàm thuần (có test)
_CHUNK_ID = re.compile(r"tea_\d+", re.IGNORECASE)
_SOURCE_TAG = re.compile(r"\[?\s*ngu[oồ]n\s*\d+\s*\]?", re.IGNORECASE)
_LIST_MARKER = re.compile(r"(?m)^\s*\d+[.)]\s+")
_NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
# "20 000" (dấu cách ngăn cách hàng nghìn) phải là một số, không phải "20" và "000"
_THOUSANDS_SPACE = re.compile(r"(?<![\d.,])(\d{1,3})((?: \d{3})+)(?!\d)")


def normalize_number(token: str) -> str:
    """So sánh số theo chữ số (bỏ dấu ngăn cách hàng nghìn/thập phân): '1.800' và '1800', '10,1' và '10.1' cùng khóa."""
    return re.sub(r"\D", "", token)


def extract_numbers(text: str) -> List[str]:
    """Các con số trong văn bản, bỏ mã chunk (tea_000154), nhãn nguồn ([Nguồn 1]) và số thứ tự danh sách."""
    cleaned = text.replace(" ", " ").replace(" ", " ")
    cleaned = _CHUNK_ID.sub(" ", cleaned)
    cleaned = _SOURCE_TAG.sub(" ", cleaned)
    cleaned = _LIST_MARKER.sub("", cleaned)
    cleaned = _THOUSANDS_SPACE.sub(lambda m: m.group(1) + m.group(2).replace(" ", ""), cleaned)
    return [normalize_number(m.group()) for m in _NUMBER.finditer(cleaned)]


def unsupported_numbers(answer: str, context: str, question: str) -> List[str]:
    """Số trong câu trả lời không xuất hiện trong ngữ cảnh hoặc câu hỏi (dấu hiệu bịa số liệu)."""
    allowed = set(extract_numbers(context)) | set(extract_numbers(question))
    return sorted({n for n in extract_numbers(answer) if n and n not in allowed})


def _words(text: str) -> List[str]:
    return re.findall(r"\w+", _CHUNK_ID.sub(" ", text.lower().replace(" ", " ")))


def copy_ratio(answer: str, context: str, n: int = 6) -> Optional[float]:
    """
    Tỉ lệ cụm n từ liên tiếp của câu trả lời xuất hiện NGUYÊN VĂN trong ngữ cảnh.
    Gần 1 nghĩa là chép lại đoạn tài liệu; thấp nghĩa là đã diễn đạt lại/chọn lọc. Số liệu và tên riêng bị trùng
    nguyên văn là bình thường nên không kỳ vọng bằng 0.
    """
    answer_words = _words(answer)
    if len(answer_words) < n:
        return None
    context_words = _words(context)
    context_grams = {tuple(context_words[i:i + n]) for i in range(len(context_words) - n + 1)}
    grams = [tuple(answer_words[i:i + n]) for i in range(len(answer_words) - n + 1)]
    return sum(g in context_grams for g in grams) / len(grams)


_STRUCTURE = re.compile(r"(?m)^\s*(?:[-*•]\s|\d+[.)]\s|\|.+\|)|\*\*[^*]+\*\*")


def is_structured(answer: str) -> bool:
    """Có gạch đầu dòng, danh sách đánh số, bảng hoặc tiêu đề in đậm."""
    return _STRUCTURE.search(answer) is not None


def has_style_noise(answer: str) -> bool:
    """Ghi mã nguồn (tea_...) hoặc phần "Lưu ý" thừa trong nội dung; giao diện đã hiển thị nguồn riêng."""
    return _CHUNK_ID.search(answer) is not None or re.search(r"(?im)^\W*(?:>\s*)?\W*l[uư]u\s*[yý]", answer) is not None


def is_refusal(answer: str) -> bool:
    lowered = answer.lower()
    if lowered.startswith(NO_KNOWLEDGE_ANSWER[:40].lower()):
        return True
    return len(answer) <= LLM_REFUSAL_MAX_CHARS and LLM_REFUSAL_MARKER in lowered


def parse_judge_json(raw: str) -> Optional[Dict[str, Any]]:
    """Lấy JSON từ đầu ra của model chấm (có thể kèm khối suy luận <think> hoặc rào ```json)."""
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    if not isinstance(data.get("claims"), list):
        return None
    return data


def faithfulness(claims: List[Dict[str, Any]]) -> Optional[float]:
    if not claims:
        return None
    return sum(1 for c in claims if c.get("supported") is True) / len(claims)


def mean(values: List[float]) -> Optional[float]:
    return statistics.fmean(values) if values else None


def summarize(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    in_domain = [r for r in records if r["type"] == "in_domain"]
    out_scope = [r for r in records if r["type"] != "in_domain"]
    judged = [r for r in in_domain if r.get("judge")]
    return {
        "n_in_domain": len(in_domain),
        "n_out_of_scope": len(out_scope),
        "wrongly_refused": sum(1 for r in in_domain if r["refused"]),
        "wrongly_answered": sum(1 for r in out_scope if not r["refused"]),
        "answers_with_unsupported_numbers": sum(1 for r in in_domain if r["unsupported_numbers"]),
        "n_judged": len(judged),
        "faithfulness": mean([r["judge"]["faithfulness"] for r in judged if r["judge"]["faithfulness"] is not None]),
        "relevance": mean([r["judge"]["relevance"] for r in judged if isinstance(r["judge"].get("relevance"), (int, float))]),
        "completeness": mean([r["judge"]["completeness"] for r in judged if isinstance(r["judge"].get("completeness"), (int, float))]),
        "judge_failures": sum(1 for r in in_domain if r.get("judge_error")),
        # Chỉ tính các câu thật sự gọi LLM; câu bị cổng chặn trả lời gần như tức thì và sẽ làm số liệu sai lệch
        "avg_latency_s": mean([r["latency_s"] for r in records if r["latency_s"] is not None and r["gate_relevant"]]),
        "avg_words": mean([r["words"] for r in in_domain if r.get("words") and not r["refused"]]),
        "avg_copy_ratio": mean([r["copy_ratio"] for r in in_domain if r.get("copy_ratio") is not None]),
        "structured_rate": mean([1.0 if r["structured"] else 0.0 for r in in_domain if not r["refused"] and "structured" in r]),
        "style_noise": sum(1 for r in in_domain if r.get("style_noise")),
        "over_150_words": sum(1 for r in in_domain if not r["refused"] and (r.get("words") or 0) > 150),
    }


# ---------------------------------------------------------------- gọi model
async def _with_retry(make_call, attempts: int = 6):
    """Groq gói miễn phí giới hạn tần suất; thử lại với thời gian chờ tăng dần."""
    delay = 4.0
    for attempt in range(attempts):
        try:
            return await make_call()
        except HTTPException as err:
            if err.status_code not in (429, 502, 503, 504) or attempt == attempts - 1:
                raise
        except Exception:
            if attempt == attempts - 1:
                raise
        await asyncio.sleep(delay)
        delay = min(delay * 2, 60)


async def generate_answer(model: str, question: str, context: str) -> str:
    settings.GROQ_MODEL = model
    return await _with_retry(lambda: llm_service.generate_rag_response(query=question, context_text=context))


async def judge_answer(judge_model: str, question: str, context: str, answer: str) -> Optional[Dict[str, Any]]:
    client = AsyncOpenAI(api_key=settings.GROQ_API_KEY, base_url=settings.GROQ_BASE_URL)
    prompt = JUDGE_PROMPT.format(question=question, context=context[: settings.MAX_CONTEXT_CHARS], answer=answer)

    async def call() -> str:
        res = await client.chat.completions.create(
            model=judge_model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=3000,
        )
        return res.choices[0].message.content or ""

    raw = await _with_retry(call)
    parsed = parse_judge_json(raw)
    if parsed is None:
        return None
    claims = parsed["claims"]
    return {
        "claims": claims,
        "faithfulness": faithfulness(claims),
        "relevance": parsed.get("relevance"),
        "completeness": parsed.get("completeness"),
        "comment": parsed.get("comment", ""),
    }


# ---------------------------------------------------------------- chạy đánh giá
def select_questions(limit: int) -> List[Dict[str, Any]]:
    """Toàn bộ câu ngoài phạm vi + mẫu câu trong phạm vi lấy đều theo bước cố định (tái lập được)."""
    queries = load_eval_set()
    in_domain = [q for q in queries if q["type"] == "in_domain"]
    out_scope = [q for q in queries if q["type"] != "in_domain"]
    step = max(1, len(in_domain) // max(1, limit))
    return in_domain[::step][:limit] + out_scope


async def evaluate_pair(
    generator: str, judge: Optional[str], questions: List[Dict[str, Any]], pause_s: float
) -> List[Dict[str, Any]]:
    retriever = get_default_retriever()
    records: List[Dict[str, Any]] = []
    for i, item in enumerate(questions, 1):
        question = item["query"]
        started = time.time()
        result = retriever.retrieve(question, top_k=RETRIEVAL_TOP_K)
        context = result["context_text"] if result["is_relevant"] else ""
        record: Dict[str, Any] = {
            "id": item["id"], "type": item["type"], "question": question,
            "gate_relevant": result["is_relevant"], "answer": None, "refused": False,
            "unsupported_numbers": [], "latency_s": None, "judge": None, "judge_error": None,
        }
        try:
            if not result["is_relevant"]:
                record["answer"] = NO_KNOWLEDGE_ANSWER  # nhánh từ chối của hệ thống, không gọi LLM
            else:
                record["answer"] = await generate_answer(generator, question, context)
            record["latency_s"] = round(time.time() - started, 2)
            record["refused"] = is_refusal(record["answer"])
            record["words"] = len(record["answer"].split())
            record["structured"] = is_structured(record["answer"])
            record["style_noise"] = has_style_noise(record["answer"])
            record["copy_ratio"] = copy_ratio(record["answer"], context) if context else None
            if item["type"] == "in_domain" and not record["refused"]:
                record["unsupported_numbers"] = unsupported_numbers(record["answer"], context, question)
                try:
                    if judge is None:  # chế độ chỉ đo hình thức (không gọi model chấm)
                        raise LookupError("bỏ qua chấm bằng model")
                    record["judge"] = await judge_answer(judge, question, context, record["answer"])
                    if record["judge"] is None:
                        record["judge_error"] = "không đọc được JSON của model chấm"
                except LookupError:
                    pass
                except Exception as err:  # lỗi chấm không được làm dừng cả lượt đánh giá
                    record["judge_error"] = f"{type(err).__name__}: {err}"[:200]
        except Exception as err:
            record["answer"] = f"[LỖI SINH CÂU TRẢ LỜI] {type(err).__name__}: {err}"[:300]
        records.append(record)
        print(f"  [{generator} {i}/{len(questions)}] {item['id']} refused={record['refused']} "
              f"faith={None if not record['judge'] else record['judge']['faithfulness']}", flush=True)
        await asyncio.sleep(pause_s)
    return records


def fmt(value: Optional[float], digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def render_report(runs: List[Dict[str, Any]]) -> str:
    lines = [
        "# Kết quả đánh giá chất lượng câu trả lời",
        "",
        f"Chạy lúc {datetime.now():%d/%m/%Y %H:%M}. Truy xuất: hybrid (bkai + BM25), top-{RETRIEVAL_TOP_K}. "
        "Model chấm luôn khác model sinh. Dữ liệu thô: `backend/evaluation/runs/`.",
        "",
        "| Model sinh | Model chấm | Câu trong phạm vi | Từ chối nhầm | Câu ngoài phạm vi | Trả lời nhầm | Độ bám nguồn | Đúng câu hỏi (1-5) | Đầy đủ (1-5) | Có số liệu không căn cứ | Độ trễ TB (s) | Số từ TB | Chép nguyên văn | Có cấu trúc | Ghi mã nguồn/Lưu ý thừa | Trên 150 từ |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        s = run["summary"]
        lines.append(
            f"| {run['generator']} | {run['judge']} | {s['n_in_domain']} | {s['wrongly_refused']} | {s['n_out_of_scope']} | "
            f"{s['wrongly_answered']} | {fmt(s['faithfulness'])} | {fmt(s['relevance'], 2)} | {fmt(s['completeness'], 2)} | "
            f"{s['answers_with_unsupported_numbers']} | {fmt(s['avg_latency_s'], 1)} | {fmt(s['avg_words'], 0)} | {fmt(s['avg_copy_ratio'], 2)} | {fmt(s['structured_rate'], 2)} | {s['style_noise']} | {s['over_150_words']} |"
        )
    lines += ["", "Độ bám nguồn = tỉ lệ mệnh đề được ngữ cảnh chứng minh (trung bình theo câu). "
              "\"Số liệu không căn cứ\" = số câu trả lời có con số không xuất hiện trong ngữ cảnh hay câu hỏi.", ""]
    for run in runs:
        lines += [f"## Mệnh đề bị chấm \"không có căn cứ\" — {run['generator']} (chấm bởi {run['judge']})", ""]
        found = False
        for r in run["records"]:
            bad = [c["claim"] for c in (r["judge"] or {}).get("claims", []) if c.get("supported") is not True]
            if bad or r["unsupported_numbers"]:
                found = True
                lines.append(f"- **{r['id']}** — {r['question']}")
                for claim in bad:
                    lines.append(f"  - mệnh đề: {claim}")
                if r["unsupported_numbers"]:
                    lines.append(f"  - số không có trong ngữ cảnh: {', '.join(r['unsupported_numbers'])}")
        if not found:
            lines.append("_Không có._")
        lines.append("")
    return "\n".join(lines) + "\n"


async def run(pairs: List[Tuple[str, Optional[str]]], limit: int, pause_s: float, report: Optional[str], tag: str = "") -> None:
    questions = select_questions(limit)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    runs = []
    for generator, judge in pairs:
        print(f"== sinh: {generator} | chấm: {judge} | {len(questions)} câu", flush=True)
        records = await evaluate_pair(generator, judge, questions, pause_s)
        run_data = {"generator": generator, "judge": judge, "summary": summarize(records), "records": records}
        runs.append(run_data)
        safe = generator.replace("/", "_")
        (RUNS_DIR / f"answer_eval_{safe}{tag}_{datetime.now():%Y%m%d_%H%M%S}.json").write_text(
            json.dumps(run_data, ensure_ascii=False, indent=1), encoding="utf-8")
    text = render_report(runs)
    print(text)
    if report:
        Path(report).write_text(text, encoding="utf-8")
        print(f"Đã ghi {report}")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, default=24, help="số câu trong phạm vi được chấm")
    parser.add_argument("--pause", type=float, default=1.0, help="giây nghỉ giữa các câu (giảm chạm giới hạn tần suất)")
    parser.add_argument("--pairs", help='ví dụ "openai/gpt-oss-120b:qwen/qwen3.8-27b,..." (mặc định: ba cặp trong DEFAULT_PAIRS)')
    parser.add_argument("--report", help="ghi kết quả ra Markdown")
    parser.add_argument("--no-judge", action="store_true", help="chỉ sinh câu trả lời và đo chỉ số hình thức, không gọi model chấm")
    parser.add_argument("--tag", default="", help="nhãn thêm vào tên tệp kết quả (ví dụ _prompt_moi)")
    args = parser.parse_args()
    pairs = DEFAULT_PAIRS
    if args.pairs:
        pairs = [tuple(p.split(":", 1)) for p in args.pairs.split(",")]  # type: ignore[misc]
    if args.no_judge:
        pairs = [(g, None) for g, _ in pairs]
    asyncio.run(run(pairs, args.limit, args.pause, args.report, args.tag))


if __name__ == "__main__":
    main()
