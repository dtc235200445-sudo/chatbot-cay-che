"""
Xuất phiếu để NGƯỜI kiểm tra tính hợp lệ của bộ câu hỏi lệch từ vựng (docs/phieu_kiem_tra_cau_hoi_lech_tu.csv).

Vì câu hỏi do LLM viết lại nên có thể mơ hồ hoặc có nhiều chunk cùng trả lời được; nhãn "một chunk đúng" khi đó làm điểm truy xuất
thấp giả tạo. Người chấm điền 2 cột:
  - "câu hỏi hợp lệ?": có/không (câu hỏi rõ nghĩa, không phụ thuộc ngữ cảnh ngầm như "cây này")
  - "top-3 có chunk trả lời được?": có/không (không cần đúng chunk nhãn)
Sau khi điền, chạy rag.evaluation.score_shifted_review để tính Hit@3 "nới lỏng theo người".

Chạy: python -m rag.evaluation.export_shifted_review
"""
import csv
import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from rag.retriever import RAGRetriever
from rag.vector_store import VectorStoreManager

ROOT = Path(__file__).resolve().parent.parent.parent
SHIFTED = Path(__file__).resolve().parent / "shifted_questions.json"
SHEET = ROOT / "docs" / "phieu_kiem_tra_cau_hoi_lech_tu.csv"


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    kb = {c["chunk_id"]: c for c in json.loads((ROOT / "data" / "knowledge_base.json").read_text(encoding="utf-8"))}
    qs = [q for q in json.loads(SHIFTED.read_text(encoding="utf-8"))["questions"] if q["overlap"] <= 0.35]
    tmp = Path(tempfile.mkdtemp(prefix="review_"))
    shutil.copytree(ROOT / "database" / "chroma_db", tmp / "c")
    r = RAGRetriever(VectorStoreManager(persist_dir=str(tmp / "c")))
    r.load()
    rows = []
    for q in qs:
        top = [c["chunk_id"] for c in r.retrieve(q["question"], top_k=3)["retrieved_chunks"]]
        src = kb[q["source_chunk_id"]]
        row = {"câu hỏi": q["question"], "độ trùng từ": q["overlap"], "chunk nhãn (tiêu đề)": src["title"], "chunk nhãn (nội dung)": src["content"][:400],
               "Tea AI trúng chunk nhãn trong top-3": "có" if q["source_chunk_id"] in top else "không"}
        for i, cid in enumerate(top, 1):
            row[f"top{i} (tiêu đề)"] = kb[cid]["title"]
            row[f"top{i} (nội dung)"] = kb[cid]["content"][:400]
        row.update({"câu hỏi hợp lệ? (có/không)": "", "top-3 có chunk trả lời được? (có/không)": "", "ghi chú": ""})
        rows.append(row)
    shutil.rmtree(tmp, ignore_errors=True)
    with SHEET.open("w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"Đã ghi {len(rows)} dòng vào {SHEET}")


if __name__ == "__main__":
    main()
