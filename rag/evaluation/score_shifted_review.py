"""
Tính kết quả sau khi người đã điền phiếu kiểm tra bộ câu hỏi lệch từ vựng.

Chỉ số: số câu hợp lệ; Hit@3 chặt (đúng chunk nhãn) và Hit@3 nới lỏng theo người (top-3 có chunk trả lời được) của Tea AI,
chỉ tính trên câu được người xác nhận là hợp lệ.

Chạy: python -m rag.evaluation.score_shifted_review
"""
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rag.evaluation.run_extended_evaluation import fmt_ci

SHEET = Path(__file__).resolve().parent.parent.parent / "docs" / "phieu_kiem_tra_cau_hoi_lech_tu.csv"


def yes(v: str) -> bool:
    return v.strip().lower() in {"có", "co", "c", "yes", "y", "1", "x"}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = list(csv.DictReader(SHEET.open(encoding="utf-8-sig")))
    done = [r for r in rows if r["câu hỏi hợp lệ? (có/không)"].strip()]
    if not done:
        print("Phiếu chưa được điền.")
        return
    valid = [r for r in done if yes(r["câu hỏi hợp lệ? (có/không)"])]
    strict = sum(r["Tea AI trúng chunk nhãn trong top-3"] == "có" for r in valid)
    human = sum(yes(r["top-3 có chunk trả lời được? (có/không)"]) for r in valid)
    print(f"Đã kiểm tra {len(done)}/{len(rows)} câu; hợp lệ {len(valid)}")
    if valid:
        print("Hit@3 chặt (đúng chunk nhãn):", fmt_ci(strict, len(valid)))
        print("Hit@3 nới lỏng theo người (top-3 có chunk trả lời được):", fmt_ci(human, len(valid)))


if __name__ == "__main__":
    main()
