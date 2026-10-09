"""
Xuất phiếu chấm tay từ kết quả chạy answer_eval, để người kiểm tra mức đồng thuận với model chấm.

Chạy:  python -m backend.evaluation.export_review --generator openai/gpt-oss-120b --n 20
Ghi ra docs/answer_review_sheet.md: mỗi câu gồm câu hỏi, câu trả lời, các đoạn tài liệu (chunk) đã dùng và từng
mệnh đề mà model chấm đã đánh giá. Bạn đọc rồi điền vào cột "Người chấm" (Đúng/Sai); tỉ lệ khớp cho biết có tin
được model chấm hay không.
"""
import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

RUNS_DIR = Path(__file__).resolve().parent / "runs"


def latest_run(generator: str) -> Dict[str, Any]:
    safe = generator.replace("/", "_")
    files = sorted(RUNS_DIR.glob(f"answer_eval_{safe}_*.json"))
    if not files:
        raise SystemExit(f"Chưa có kết quả chạy cho {generator}. Chạy answer_eval trước.")
    return json.loads(files[-1].read_text(encoding="utf-8"))


def pick_judged(records: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    """Lấy đều theo bước cố định trong các câu đã được chấm (tái lập được)."""
    judged = [r for r in records if r.get("judge") and r["judge"].get("claims")]
    step = max(1, len(judged) // max(1, n))
    return judged[::step][:n]


def render_sheet(run: Dict[str, Any], n: int, context_lookup: Dict[str, str]) -> str:
    lines = [
        "# Phiếu chấm tay câu trả lời",
        "",
        f"Câu trả lời do `{run['generator']}` sinh, model chấm: `{run['judge']}`.",
        "",
        "Cách làm: với mỗi mệnh đề, đọc phần **Tài liệu** rồi điền **Người chấm** là `Đúng` (tài liệu nói rõ điều đó) hoặc `Sai` "
        "(tài liệu không nói, nói khác, hoặc chatbot tự thêm mục đích/giải thích). Sau đó đếm số dòng mà cột người chấm "
        "khớp với cột model chấm: tỉ lệ khớp từ khoảng 85% trở lên thì có thể tin số liệu tự động.",
        "",
    ]
    for r in pick_judged(run["records"], n):
        lines += [f"## {r['id']} — {r['question']}", "", "**Câu trả lời:**", "", r["answer"].strip(), ""]
        ctx = context_lookup.get(r["id"])
        if ctx:
            lines += ["**Tài liệu (ngữ cảnh đã đưa cho chatbot):**", "", ctx.strip(), ""]
        lines += ["| # | Mệnh đề | Model chấm | Người chấm |", "|---|---|---|---|"]
        for i, claim in enumerate(r["judge"]["claims"], 1):
            verdict = "Đúng" if claim.get("supported") is True else "Sai"
            text = str(claim.get("claim", "")).replace("|", "/").replace("\n", " ")
            lines.append(f"| {i} | {text} | {verdict} | |")
        lines += ["", f"Nhận xét của model chấm: {r['judge'].get('comment', '')}", ""]
    return "\n".join(lines) + "\n"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generator", default="openai/gpt-oss-120b")
    parser.add_argument("--n", type=int, default=20)
    parser.add_argument("--out", default="docs/answer_review_sheet.md")
    args = parser.parse_args()

    run = latest_run(args.generator)
    # Dựng lại ngữ cảnh bằng chính bộ truy xuất của hệ thống để người chấm thấy đúng tài liệu chatbot đã dùng
    from backend.services.assistant_service import get_default_retriever
    retriever = get_default_retriever()
    lookup = {
        r["id"]: retriever.retrieve(r["question"], top_k=3)["context_text"]
        for r in pick_judged(run["records"], args.n)
    }
    Path(args.out).write_text(render_sheet(run, args.n, lookup), encoding="utf-8")
    print(f"Đã ghi {args.out}")


if __name__ == "__main__":
    main()
