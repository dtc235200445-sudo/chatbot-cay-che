"""
So sánh tầng ANSWER: "RAG thường" (V2: embedding đa ngữ dense + prompt trả lời chung, không cổng từ chối)
với Tea AI đã có sẵn kết quả trên cùng mẫu câu hỏi (qa1000_answer_eval_*_repaired*.json).

Cùng model sinh (openai/gpt-oss-120b, cùng temperature/max_tokens/reasoning_effort như sản phẩm) và
cùng model chấm (qwen/qwen3.8-27b, cùng JUDGE_PROMPT_V2). Chỉ chạy lại phía RAG thường.

Tiết kiệm hạn mức Groq (200.000 token/ngày cho gpt-oss-120b): chỉ chạy tập con ghép cặp
(24 câu abstain + N câu/loại), lưu kết quả từng câu để chạy tiếp được, dừng ngay khi hết hạn mức ngày.

Chạy: python -m backend.evaluation.qa1000_vanilla_answer_eval --per-type 6
"""
import argparse
import asyncio
import glob
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import openai
from openai import AsyncOpenAI

from backend.config import settings
from backend.evaluation.answer_eval import extract_numbers, is_refusal, unsupported_numbers
from backend.evaluation.qa1000_answer_eval import (
    GENERATOR_MODEL,
    JUDGE_MODEL,
    build_sample,
    check_abstain_violation,
    judge_v2,
    mean,
)

ROOT = Path(__file__).resolve().parent.parent.parent
RUNS_DIR = Path(__file__).resolve().parent / "runs"
OUT_PATH = RUNS_DIR / "vanilla_answer_eval.json"
TEA_RUN_GLOB = str(RUNS_DIR / "qa1000_answer_eval_20260923_163333_repaired_repaired_repaired.json")
VANILLA_EMBEDDING = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
TOP_K = 3

VANILLA_SYSTEM = (
    "Bạn là trợ lý hỏi đáp. Hãy trả lời câu hỏi dựa trên ngữ cảnh được cung cấp. "
    "Nếu ngữ cảnh không có thông tin để trả lời, hãy nói rằng bạn không biết."
)

_BROAD_REFUSAL = re.compile(
    r"không\s+(?:có|tìm\s+thấy|đủ|nêu|đề\s+cập|cung\s+cấp|biết|rõ|thể)|chưa\s+có|xin\s+lỗi|không\s+được\s+nêu"
    r"|i.?m\s+sorry|i\s+am\s+sorry|don.?t\s+have|do\s+not\s+have|don.?t\s+know|do\s+not\s+know|no\s+information"
    r"|not\s+(?:provided|mentioned|available|specified)|cannot|can.?t\s+(?:answer|find)", re.I
)


def refused_broad(answer: str) -> bool:
    """Từ chối theo nghĩa rộng, áp dụng như nhau cho cả hai hệ thống (câu ngắn nói không có/không biết)."""
    return is_refusal(answer) or (len(answer) <= 350 and _BROAD_REFUSAL.search(answer) is not None)


class QuotaExhausted(RuntimeError):
    pass


async def chat(client: AsyncOpenAI, messages: List[Dict[str, str]]) -> str:
    kwargs: Dict[str, Any] = {
        "model": GENERATOR_MODEL, "messages": messages, "temperature": 0.2, "max_tokens": settings.GROQ_MAX_TOKENS,
    }
    if settings.GROQ_REASONING_EFFORT and GENERATOR_MODEL.startswith("openai/gpt-oss"):
        kwargs["reasoning_effort"] = settings.GROQ_REASONING_EFFORT
    delay = 4.0
    for attempt in range(6):
        try:
            res = await client.chat.completions.create(**kwargs)
            text = (res.choices[0].message.content or "").strip()
            if not text:
                kwargs["max_tokens"] = settings.GROQ_MAX_TOKENS * 2
                res = await client.chat.completions.create(**kwargs)
                text = (res.choices[0].message.content or "").strip()
            return text
        except openai.RateLimitError as err:
            msg = str(err).lower()
            if "per day" in msg or "tpd" in msg or "rpd" in msg:
                raise QuotaExhausted(str(err)[:200])
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)
        except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError):
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)
    raise RuntimeError("hết số lần thử")


def pick_subset(per_type: int, prefer=()) -> List[Dict[str, Any]]:
    """Chọn tập con ghép cặp; ưu tiên các câu đã có kết quả (prefer) để mở rộng mẫu mà không bỏ phí lượt đã chạy."""
    tea = {r["id"]: r for r in json.loads(Path(glob.glob(TEA_RUN_GLOB)[0]).read_text(encoding="utf-8"))["records"]}
    sample = build_sample()
    chosen = [r for r in sample if r["grading_mode"] == "abstain_no_data"]
    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for r in sample:
        t = tea.get(r["id"])
        if r["grading_mode"] == "semantic_factual" and t and t.get("judge"):
            by_type.setdefault(r["question_type"], []).append(r)
    for qtype, items in sorted(by_type.items()):
        items.sort(key=lambda r: r["id"])
        pref = [r for r in items if r["id"] in prefer][:per_type]
        rest = [r for r in items if r["id"] not in prefer]
        need = per_type - len(pref)
        if need > 0 and rest:
            step = max(1, len(rest) // need)
            pref += rest[::step][:need]
        chosen.extend(pref)
    return chosen


async def run(per_type: int, pause_s: float) -> None:
    from sentence_transformers import SentenceTransformer

    chunks = json.loads((ROOT / "data" / "knowledge_base.json").read_text(encoding="utf-8"))
    model = SentenceTransformer(VANILLA_EMBEDDING)
    doc_vecs = model.encode([c["content"] for c in chunks], normalize_embeddings=True, show_progress_bar=False)

    done: Dict[str, Any] = {}
    if OUT_PATH.exists():
        done = {r["id"]: r for r in json.loads(OUT_PATH.read_text(encoding="utf-8"))["records"]}
    subset = pick_subset(per_type, prefer=set(done))
    print(f"Tập con ghép cặp: {len(subset)} câu (đã có {len(done)} kết quả lưu trước đó)", flush=True)

    client = AsyncOpenAI(api_key=settings.GROQ_API_KEY, base_url=settings.GROQ_BASE_URL, max_retries=2, timeout=settings.GROQ_TIMEOUT_S)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)

    for i, row in enumerate(subset, 1):
        if row["id"] in done:
            continue
        q = row["question"]
        started = time.time()
        sims = model.encode([q], normalize_embeddings=True, show_progress_bar=False)[0] @ doc_vecs.T
        top = np.argsort(-sims)[:TOP_K]
        context = "\n\n".join(chunks[j]["content"] for j in top)[: settings.MAX_CONTEXT_CHARS]
        rec: Dict[str, Any] = {
            "id": row["id"], "question": q, "question_type": row["question_type"], "grading_mode": row["grading_mode"],
            "retrieved_ids": [chunks[j]["chunk_id"] for j in top], "hit_source_chunk": row.get("source_chunk_id") in [chunks[j]["chunk_id"] for j in top],
            "answer": None, "latency_s": None, "judge": None, "judge_error": None,
        }
        try:
            rec["answer"] = await chat(client, [
                {"role": "system", "content": VANILLA_SYSTEM},
                {"role": "user", "content": f"Ngữ cảnh:\n{context}\n\nCâu hỏi: {q}\n\nTrả lời:"},
            ])
            rec["latency_s"] = round(time.time() - started, 2)
            rec["refused"] = refused_broad(rec["answer"])
            rec["unsupported_numbers"] = unsupported_numbers(rec["answer"], context, q)
            if row["grading_mode"] == "abstain_no_data":
                rec["abstain_violation"] = (not rec["refused"]) and len(extract_numbers(rec["answer"])) > 0
            elif not rec["refused"]:
                key_points = row.get("answer_key_points") or []
                if isinstance(key_points, str):
                    key_points = json.loads(key_points)
                try:
                    rec["judge"] = await judge_v2(q, context, row["expected_answer"], key_points, rec["answer"])
                except Exception as err:  # noqa: BLE001
                    rec["judge_error"] = f"{type(err).__name__}: {err}"[:200]
        except QuotaExhausted as err:
            print(f"DỪNG: hết hạn mức ngày ({err})", flush=True)
            break
        except Exception as err:  # noqa: BLE001
            rec["answer"] = f"[LỖI] {type(err).__name__}: {err}"[:300]
        done[row["id"]] = rec
        OUT_PATH.write_text(json.dumps({"records": list(done.values())}, ensure_ascii=False, indent=1), encoding="utf-8")
        j = rec["judge"]
        print(f"  [{i}/{len(subset)}] {row['id']} ({row['question_type']}) refused={rec.get('refused')} "
              f"correctness={j['correctness'] if j else '—'}", flush=True)
        await asyncio.sleep(pause_s)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--per-type", type=int, default=6)
    parser.add_argument("--pause", type=float, default=1.0)
    args = parser.parse_args()
    asyncio.run(run(args.per_type, args.pause))


if __name__ == "__main__":
    main()
