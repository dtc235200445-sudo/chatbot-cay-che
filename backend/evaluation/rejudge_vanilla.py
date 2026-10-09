"""
Chấm bù các câu trả lời RAG thường (cấu hình chính) bị bỏ sót vì model chấm hết hạn mức lúc chạy.
Dựng lại đúng ngữ cảnh đã dùng (top-3 chunk theo retrieved_ids), cùng model chấm qwen3.8-27b và prompt chấm như các câu khác.

Chạy: python -m backend.evaluation.rejudge_vanilla
"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.config import settings
from backend.evaluation import qa1000_answer_eval as base
from backend.evaluation.qa1000_vanilla_answer_eval import OUT_PATH, refused_broad

ROOT = Path(__file__).resolve().parent.parent.parent


async def main():
    kb = {c["chunk_id"]: c["content"] for c in json.loads((ROOT / "data" / "knowledge_base.json").read_text(encoding="utf-8"))}
    rows = {r["id"]: r for r in base.build_sample()}
    data = json.loads(OUT_PATH.read_text(encoding="utf-8"))
    todo = [r for r in data["records"] if r["grading_mode"] == "semantic_factual" and not r.get("judge")
            and r.get("answer") and not refused_broad(r["answer"])]
    print(f"{len(todo)} câu cần chấm bù", flush=True)
    for n, rec in enumerate(todo, 1):
        row = rows[rec["id"]]
        context = "\n\n".join(kb[i] for i in rec["retrieved_ids"])[: settings.MAX_CONTEXT_CHARS]
        kp = row.get("answer_key_points") or []
        if isinstance(kp, str):
            kp = json.loads(kp)
        try:
            rec["judge"] = await base.judge_v2(row["question"], context, row["expected_answer"], kp, rec["answer"])
            rec["judge_error"] = None
        except Exception as err:  # noqa: BLE001
            rec["judge_error"] = f"{type(err).__name__}: {err}"[:200]
            print("DỪNG:", rec["judge_error"][:120], flush=True)
            break
        OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  [{n}/{len(todo)}] {rec['id']} correctness={rec['judge']['correctness'] if rec['judge'] else '—'}", flush=True)
        await asyncio.sleep(1)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main())
