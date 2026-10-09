"""
So sánh ghép cặp Tea AI và RAG thường với MODEL SINH và MODEL CHẤM tùy chọn (khắc phục hạn chế: trước đó chỉ một model sinh).

Mỗi câu hỏi chạy lần lượt qua hai hệ thống (nên chạy dở vẫn ghép cặp được):
  - tea     : truy xuất hybrid + cổng từ chối + prompt ràng buộc của sản phẩm (giống qa1000_answer_eval.py)
  - vanilla : embedding đa ngữ dense top-3 + prompt chung, không cổng
Model chấm nên KHÁC họ với model sinh. Kết quả lưu từng câu (chạy tiếp được), dừng ngay khi hết hạn mức ngày.

Chạy ví dụ:
  python -m backend.evaluation.qa_pair_eval --generator qwen/qwen3.8-27b --judge openai/gpt-oss-20b --per-type 4 --abstain 8
"""
import argparse
import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np
import openai
from openai import AsyncOpenAI

from backend.config import settings
from backend.evaluation import qa1000_answer_eval as base
from backend.evaluation.answer_eval import extract_numbers, generate_answer, is_refusal, unsupported_numbers
from backend.evaluation.qa1000_vanilla_answer_eval import (
    TOP_K, VANILLA_EMBEDDING, VANILLA_SYSTEM, QuotaExhausted, pick_subset, refused_broad,
)
from backend.services.assistant_service import get_default_retriever

ROOT = Path(__file__).resolve().parent.parent.parent
RUNS_DIR = Path(__file__).resolve().parent / "runs"
REFUSAL_TEXT = "Hiện tại cơ sở tri thức chưa tìm thấy nguồn thông tin đủ phù hợp để giải đáp chính xác câu hỏi này."


def slug(m: str) -> str:
    return m.replace("/", "_").replace(".", "-")


def is_day_quota(err: Exception) -> bool:
    m = str(err).lower()
    return "per day" in m or "tpd" in m or "rpd" in m or "hết hạn mức" in m


async def vanilla_generate(client: AsyncOpenAI, model: str, question: str, context: str) -> str:
    kwargs: Dict[str, Any] = {
        "model": model, "temperature": 0.2, "max_tokens": settings.GROQ_MAX_TOKENS,
        "messages": [{"role": "system", "content": VANILLA_SYSTEM},
                     {"role": "user", "content": f"Ngữ cảnh:\n{context}\n\nCâu hỏi: {question}\n\nTrả lời:"}],
    }
    if settings.GROQ_REASONING_EFFORT and model.startswith("openai/gpt-oss"):
        kwargs["reasoning_effort"] = settings.GROQ_REASONING_EFFORT
    delay = 4.0
    for _ in range(6):
        try:
            res = await client.chat.completions.create(**kwargs)
            text = (res.choices[0].message.content or "").strip()
            if not text:
                kwargs["max_tokens"] *= 2
                res = await client.chat.completions.create(**kwargs)
                text = (res.choices[0].message.content or "").strip()
            return text
        except openai.RateLimitError as err:
            if is_day_quota(err):
                raise QuotaExhausted(str(err)[:160])
            await asyncio.sleep(delay); delay = min(delay * 2, 60)
        except (openai.APIConnectionError, openai.APITimeoutError, openai.InternalServerError):
            await asyncio.sleep(delay); delay = min(delay * 2, 60)
    raise RuntimeError("hết số lần thử")


async def judge(row: Dict[str, Any], context: str, answer: str, judge_model: str):
    base.JUDGE_MODEL = judge_model
    key_points = row.get("answer_key_points") or []
    if isinstance(key_points, str):
        key_points = json.loads(key_points)
    try:
        return await base.judge_v2(row["question"], context, row["expected_answer"], key_points, answer), None
    except Exception as err:  # noqa: BLE001
        if is_day_quota(err) or "RateLimit" in type(err).__name__:
            raise QuotaExhausted(f"model chấm: {str(err)[:140]}")
        return None, f"{type(err).__name__}: {err}"[:200]


async def run(args) -> None:
    from sentence_transformers import SentenceTransformer

    out = RUNS_DIR / f"pair_{slug(args.generator)}__judge_{slug(args.judge)}.json"
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    recs: Dict[str, Any] = {}
    if out.exists():
        recs = {f"{r['system']}:{r['id']}": r for r in json.loads(out.read_text(encoding="utf-8"))["records"]}

    ab_all = [r for r in pick_subset(args.per_type, prefer=set()) if r["grading_mode"] == "abstain_no_data"]
    sem = [r for r in pick_subset(args.per_type, prefer=set()) if r["grading_mode"] == "semantic_factual"]
    step = max(1, len(ab_all) // max(1, args.abstain))
    subset = sem + ab_all[::step][: args.abstain]
    print(f"Sinh: {args.generator} | Chấm: {args.judge} | {len(sem)} câu có đáp án + {len(subset) - len(sem)} câu thiếu dữ liệu", flush=True)

    chunks = json.loads((ROOT / "data" / "knowledge_base.json").read_text(encoding="utf-8"))
    emb = SentenceTransformer(VANILLA_EMBEDDING)
    doc_vecs = emb.encode([c["content"] for c in chunks], normalize_embeddings=True, show_progress_bar=False)
    tea = get_default_retriever()
    client = AsyncOpenAI(api_key=settings.GROQ_API_KEY, base_url=settings.GROQ_BASE_URL, max_retries=2, timeout=settings.GROQ_TIMEOUT_S)

    def save():
        out.write_text(json.dumps({"generator": args.generator, "judge": args.judge, "records": list(recs.values())}, ensure_ascii=False, indent=1), encoding="utf-8")

    for i, row in enumerate(subset, 1):
        for system in ("tea", "vanilla"):
            key = f"{system}:{row['id']}"
            rec = recs.get(key)
            if rec and str(rec.get("answer", "")).startswith("[LỖI"):
                rec = None  # lượt trước lỗi (hết hạn mức, mạng...) -> sinh lại
            if rec and not rec.get("judge_pending"):
                continue
            q = row["question"]
            try:
                if not rec:
                    started = time.time()
                    if system == "tea":
                        res = tea.retrieve(q, top_k=3)
                        gate = bool(res["is_relevant"])
                        context = res["context_text"] if gate else ""
                        retrieved = [c["chunk_id"] for c in res["retrieved_chunks"]]
                        answer = await generate_answer(args.generator, q, context) if gate else REFUSAL_TEXT
                    else:
                        top = np.argsort(-(emb.encode([q], normalize_embeddings=True, show_progress_bar=False)[0] @ doc_vecs.T))[:TOP_K]
                        retrieved = [chunks[j]["chunk_id"] for j in top]
                        context = "\n\n".join(chunks[j]["content"] for j in top)[: settings.MAX_CONTEXT_CHARS]
                        gate = True
                        answer = await vanilla_generate(client, args.generator, q, context)
                    rec = {
                        "id": row["id"], "system": system, "question_type": row["question_type"], "grading_mode": row["grading_mode"],
                        "gate_relevant": gate, "retrieved_ids": retrieved, "hit_source_chunk": row.get("source_chunk_id") in retrieved,
                        "context": context, "answer": answer, "latency_s": round(time.time() - started, 2),
                        "context_chars": len(context), "answer_words": len(answer.split()),
                        "refused": (is_refusal(answer) or not gate) if system == "tea" else refused_broad(answer),
                        "unsupported_numbers": unsupported_numbers(answer, context, q) if context else [],
                        "judge": None, "judge_error": None, "judge_pending": False,
                    }
                    if row["grading_mode"] == "abstain_no_data":
                        rec["abstain_violation"] = (not rec["refused"]) and len(extract_numbers(answer)) > 0
                    recs[key] = rec
                if row["grading_mode"] == "semantic_factual" and not rec["refused"] and rec["gate_relevant"] and rec["judge"] is None:
                    jd, err = await judge(row, rec["context"], rec["answer"], args.judge)
                    rec["judge"], rec["judge_error"], rec["judge_pending"] = jd, err, False
            except QuotaExhausted as err:
                if key in recs:
                    recs[key]["judge_pending"] = recs[key]["judge"] is None and row["grading_mode"] == "semantic_factual" and not recs[key]["refused"]
                save()
                print(f"DỪNG: hết hạn mức ngày ({err})", flush=True)
                return
            except Exception as err:  # noqa: BLE001
                if is_day_quota(err):
                    save()
                    print(f"DỪNG: hết hạn mức (Tea AI/LLM service): {str(err)[:120]}", flush=True)
                    return
                recs[key] = {"id": row["id"], "system": system, "question_type": row["question_type"], "grading_mode": row["grading_mode"],
                             "answer": f"[LỖI] {type(err).__name__}: {err}"[:300], "refused": False, "judge": None, "judge_error": "lỗi sinh",
                             "gate_relevant": True, "unsupported_numbers": [], "judge_pending": False, "context": "", "retrieved_ids": [], "hit_source_chunk": False}
            save()
            j = recs[key].get("judge")
            print(f"  [{i}/{len(subset)}] {row['id']} {system:7s} ({row['question_type']}) refused={recs[key].get('refused')} correctness={j['correctness'] if j else '—'}", flush=True)
            await asyncio.sleep(args.pause)
    print("XONG", flush=True)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--generator", required=True)
    ap.add_argument("--judge", required=True)
    ap.add_argument("--per-type", type=int, default=4)
    ap.add_argument("--abstain", type=int, default=8)
    ap.add_argument("--pause", type=float, default=1.0)
    asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    main()
