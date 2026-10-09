"""
Chạy lại đúng các câu bị lỗi hạ tầng (rate limit/timeout Groq) trong lần chạy answer-eval gần nhất,
gộp kết quả vào và ghi lại báo cáo — tránh phải chạy lại toàn bộ 150 câu (tốn quota).

Chạy: python -m backend.evaluation.qa1000_repair_failed
"""
import asyncio
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.evaluation.qa1000_answer_eval import (
    RUNS_DIR,
    evaluate,
    load_dataset,
    render_report,
    summarize,
)

REPORT_PATH = Path("docs/QA1000_ANSWER_RESULTS.md")


def is_infra_failure(r) -> bool:
    return (r["answer"] or "").startswith("[LỖI SINH CÂU TRẢ LỜI]") or bool(r.get("judge_error"))


async def main():
    latest = sorted(glob.glob(str(RUNS_DIR / "qa1000_answer_eval_*.json")))[-1]
    print(f"Nạp lần chạy gần nhất: {latest}")
    data = json.loads(Path(latest).read_text(encoding="utf-8"))
    records = data["records"]

    failed_ids = {r["id"] for r in records if is_infra_failure(r)}
    print(f"Số câu cần chạy lại: {len(failed_ids)} -> {sorted(failed_ids)}")

    all_rows = {r["id"]: r for r in load_dataset()}
    retry_rows = [all_rows[i] for i in failed_ids]

    new_records = await evaluate(retry_rows, pause_s=3.0)

    by_id = {r["id"]: r for r in records}
    for r in new_records:
        still_failed = is_infra_failure(r)
        print(f"  {r['id']}: {'VẪN LỖI' if still_failed else 'OK'}")
        by_id[r["id"]] = r

    merged = list(by_id.values())
    summary = summarize(merged)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out = RUNS_DIR / (Path(latest).stem + "_repaired.json")
    out.write_text(json.dumps({"summary": summary, "records": merged}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Đã ghi: {out}")

    text = render_report(merged, summary)
    REPORT_PATH.write_text(text, encoding="utf-8")
    print(f"Đã ghi lại: {REPORT_PATH}")
    print(text)

    remaining_failed = [r["id"] for r in merged if is_infra_failure(r)]
    if remaining_failed:
        print(f"\nVẪN CÒN LỖI (cần chạy lại lần nữa): {remaining_failed}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    asyncio.run(main())
