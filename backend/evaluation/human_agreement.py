"""
Tính mức đồng thuận giữa người chấm và model chấm trên phiếu chấm tay đã điền (docs/phieu_cham_tay_30_cap.csv).

Chỉ số:
  - Tea AI hơn / hòa / kém RAG thường theo người so với theo model chấm; tỉ lệ đồng ý về hướng hơn-kém.
  - Tương quan Spearman giữa điểm người và điểm model chấm (correctness, 1-5).
  - Điểm trung bình theo người của từng hệ thống.

Chạy: python -m backend.evaluation.human_agreement
"""
import csv
import glob
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np

from backend.evaluation.pair_report import KEY, SHEET, load_primary


def rank(v):
    order = np.argsort(v)
    r = np.empty(len(v))
    r[order] = np.arange(len(v))
    for val in set(v):  # xử lý điểm bằng nhau: lấy hạng trung bình
        idx = [i for i, x in enumerate(v) if x == val]
        r[idx] = np.mean(r[idx])
    return r


def spearman(a, b):
    if len(a) < 3 or len(set(a)) < 2 or len(set(b)) < 2:
        return None
    return float(np.corrcoef(rank(list(a)), rank(list(b)))[0, 1])


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    key = json.loads(KEY.read_text(encoding="utf-8"))
    _, _, tea, van = load_primary()
    rows = list(csv.DictReader(SHEET.open(encoding="utf-8-sig")))
    filled = [r for r in rows if r["điểm A (1-5)"].strip() and r["điểm B (1-5)"].strip()]
    if not filled:
        print("Phiếu chưa được điền điểm.")
        return
    h_tea, h_van, m_tea, m_van = [], [], [], []
    for r in filled:
        i = r["id"]
        a, b = float(r["điểm A (1-5)"]), float(r["điểm B (1-5)"])
        tea_h, van_h = (a, b) if key[i]["A"] == "Tea AI" else (b, a)
        h_tea.append(tea_h); h_van.append(van_h)
        m_tea.append(tea[i]["judge"]["correctness"]); m_van.append(van[i]["judge"]["correctness"])
    sign = lambda x: (x > 0) - (x < 0)
    agree = sum(sign(ht - hv) == sign(mt - mv) for ht, hv, mt, mv in zip(h_tea, h_van, m_tea, m_van)) / len(filled)
    print(f"Số cặp đã chấm: {len(filled)}")
    print(f"Điểm TB theo người: Tea AI {np.mean(h_tea):.2f} | RAG thường {np.mean(h_van):.2f}")
    print(f"Điểm TB theo model chấm: Tea AI {np.mean(m_tea):.2f} | RAG thường {np.mean(m_van):.2f}")
    print(f"Đồng ý về hướng hơn/hòa/kém giữa người và model chấm: {agree:.1%}")
    print(f"Spearman người vs model (Tea AI): {spearman(h_tea, m_tea)}")
    print(f"Spearman người vs model (RAG thường): {spearman(h_van, m_van)}")


if __name__ == "__main__":
    main()
