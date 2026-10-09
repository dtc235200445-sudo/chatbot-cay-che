"""
Đánh giá tầng RETRIEVAL trên bộ 1000 câu hỏi (E:/NHÁP 2/tea_chatbot_qa_test_1000.jsonl).

Chỉ chạy embedding + BM25 cục bộ, KHÔNG gọi LLM — nên chạy được trên toàn bộ
928 câu thuộc phạm vi RAG (loại bỏ 72 câu "Tea_Regions_Project_Config" vì nguồn
đó không được ingest vào ChromaDB, không thuộc phạm vi truy xuất RAG).

Chỉ số tính: Hit@1/3/5, MRR, nDCG@3 (giống rag/evaluation/run_eval.py, nhưng
trên bộ câu hỏi lớn hơn nhiều và có breakdown theo question_type/difficulty),
cùng Context Recall xấp xỉ (không dùng LLM): coverage của answer_key_points
theo cosine similarity với các chunk truy xuất được.

Chạy: python -m rag.evaluation.run_qa1000_retrieval
"""
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np

from rag import config
from rag.retriever import RAGRetriever
from rag.text_utils import fold_diacritics

DATASET_PATH = Path(r"E:\NHÁP 2\tea_chatbot_qa_test_1000.jsonl")
REPORT_MD = Path(__file__).resolve().parent.parent.parent / "docs" / "QA1000_RETRIEVAL_RESULTS.md"
REPORT_JSON = Path(__file__).resolve().parent / "qa1000_retrieval_raw.json"

TOP_K = 5
CONTEXT_RECALL_TOP_K = 3
# Ngưỡng coi 1 key point là "được bao phủ" bởi context truy xuất được.
# Dùng chung STRONG_COSINE của cổng liên quan (rag/config.py) để nhất quán,
# nhưng đây là ước lượng bằng cosine, KHÔNG phải LLM chấm attribution như RAGAS gốc.
CONTEXT_RECALL_COSINE_THRESHOLD = 0.50


def load_dataset():
    rows = [json.loads(l) for l in DATASET_PATH.open(encoding="utf-8")]
    rag_rows = [r for r in rows if r["dataset"] != "Tea_Regions_Project_Config"]
    region_rows = [r for r in rows if r["dataset"] == "Tea_Regions_Project_Config"]
    return rag_rows, region_rows


def dcg_at_k(rank: int, k: int) -> float:
    """rank: vị trí 1-based của chunk đúng, hoặc None nếu không có trong top-k."""
    if rank is None or rank > k:
        return 0.0
    return 1.0 / math.log2(rank + 1)


def main():
    rag_rows, region_rows = load_dataset()
    print(f"Tổng câu hỏi: {len(rag_rows) + len(region_rows)} | thuộc phạm vi RAG: {len(rag_rows)} "
          f"| ngoài phạm vi RAG (Tea_Regions_Project_Config, bỏ qua tầng retrieval): {len(region_rows)}")

    retriever = RAGRetriever()
    retriever.load()
    snapshot = retriever._snapshot
    id_to_idx = {cid: i for i, cid in enumerate(snapshot.ids)}

    per_row = []
    for i, row in enumerate(rag_rows, 1):
        result = retriever.retrieve(query=row["question"], top_k=TOP_K)
        retrieved_ids = [c["chunk_id"] for c in result["retrieved_chunks"]]
        true_id = row["source_chunk_id"]
        rank = (retrieved_ids.index(true_id) + 1) if true_id in retrieved_ids else None

        # Context Recall xấp xỉ: coverage của answer_key_points bằng cosine với top-3 chunk truy xuất.
        key_points = row.get("answer_key_points") or []
        if isinstance(key_points, str):
            try:
                key_points = json.loads(key_points)
            except json.JSONDecodeError:
                key_points = [key_points]
        covered = 0
        if key_points:
            top_ids = retrieved_ids[:CONTEXT_RECALL_TOP_K]
            top_idx = [id_to_idx[c] for c in top_ids if c in id_to_idx]
            if top_idx:
                unaccented = row.get("question", "") and fold_diacritics(row["question"]) == row["question"].lower()
                doc_vecs = snapshot.embeddings_folded[top_idx] if unaccented else snapshot.embeddings[top_idx]
                # Mã hoá cả các key point của 1 câu trong một lần gọi (nhanh hơn nhiều so với từng câu)
                kp_vecs = retriever.vector_store._engine().encode(key_points)
                sims = kp_vecs @ doc_vecs.T  # (n_kp, n_top)
                max_sim = sims.max(axis=1)
                covered = int((max_sim >= CONTEXT_RECALL_COSINE_THRESHOLD).sum())
        context_recall = covered / len(key_points) if key_points else None

        per_row.append({
            "id": row["id"],
            "question_type": row["question_type"],
            "difficulty": row["difficulty"],
            "dataset": row["dataset"],
            "rank": rank,
            "hit1": rank == 1,
            "hit3": rank is not None and rank <= 3,
            "hit5": rank is not None and rank <= 5,
            "rr": (1.0 / rank) if rank else 0.0,
            "ndcg3": dcg_at_k(rank, 3),  # IDCG@3 = 1 (chỉ có 1 chunk liên quan/câu) nên DCG = nDCG
            "context_recall": context_recall,
        })
        if i % 100 == 0:
            print(f"  ... {i}/{len(rag_rows)}")

    REPORT_JSON.write_text(json.dumps(per_row, ensure_ascii=False, indent=2), encoding="utf-8")

    def agg(rows):
        n = len(rows)
        if n == 0:
            return None
        cr_vals = [r["context_recall"] for r in rows if r["context_recall"] is not None]
        return {
            "n": n,
            "hit1": sum(r["hit1"] for r in rows) / n,
            "hit3": sum(r["hit3"] for r in rows) / n,
            "hit5": sum(r["hit5"] for r in rows) / n,
            "mrr": sum(r["rr"] for r in rows) / n,
            "ndcg3": sum(r["ndcg3"] for r in rows) / n,
            "context_recall": (sum(cr_vals) / len(cr_vals)) if cr_vals else None,
        }

    overall = agg(per_row)
    by_qtype = {}
    for qtype in sorted(set(r["question_type"] for r in per_row)):
        by_qtype[qtype] = agg([r for r in per_row if r["question_type"] == qtype])
    by_diff = {}
    for diff in ["easy", "medium", "hard"]:
        by_diff[diff] = agg([r for r in per_row if r["difficulty"] == diff])
    by_dataset = {}
    for ds in sorted(set(r["dataset"] for r in per_row)):
        by_dataset[ds] = agg([r for r in per_row if r["dataset"] == ds])

    lines = []
    lines.append("# Kết quả đánh giá Retrieval trên bộ 1000 câu hỏi\n")
    lines.append(f"Nguồn: `{DATASET_PATH}`. Tổng {len(rag_rows) + len(region_rows)} câu, "
                  f"trong đó **{len(rag_rows)} câu thuộc phạm vi RAG** được đánh giá ở đây "
                  f"(loại {len(region_rows)} câu `Tea_Regions_Project_Config` vì nguồn này không được "
                  f"ingest vào ChromaDB, không đi qua RAG retriever).\n")
    lines.append(f"Ngưỡng Context Recall (xấp xỉ, dựa cosine, KHÔNG phải LLM chấm attribution như RAGAS gốc): "
                  f"cosine ≥ {CONTEXT_RECALL_COSINE_THRESHOLD} giữa key point và top-{CONTEXT_RECALL_TOP_K} chunk truy xuất.\n")

    lines.append("\n## Tổng thể\n")
    lines.append("| N | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 | Context Recall (xấp xỉ) |")
    lines.append("|---|---|---|---|---|---|---|")
    o = overall
    lines.append(f"| {o['n']} | {o['hit1']:.3f} | {o['hit3']:.3f} | {o['hit5']:.3f} | {o['mrr']:.3f} | "
                  f"{o['ndcg3']:.3f} | {o['context_recall']:.3f} |")

    lines.append("\n## Theo question_type\n")
    lines.append("| question_type | N | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 | Context Recall |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for k, v in by_qtype.items():
        if v:
            lines.append(f"| {k} | {v['n']} | {v['hit1']:.3f} | {v['hit3']:.3f} | {v['hit5']:.3f} | "
                          f"{v['mrr']:.3f} | {v['ndcg3']:.3f} | {v['context_recall']:.3f} |")

    lines.append("\n## Theo difficulty\n")
    lines.append("| difficulty | N | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 | Context Recall |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for k, v in by_diff.items():
        if v:
            lines.append(f"| {k} | {v['n']} | {v['hit1']:.3f} | {v['hit3']:.3f} | {v['hit5']:.3f} | "
                          f"{v['mrr']:.3f} | {v['ndcg3']:.3f} | {v['context_recall']:.3f} |")

    lines.append("\n## Theo nguồn (dataset)\n")
    lines.append("| dataset | N | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 | Context Recall |")
    lines.append("|---|---|---|---|---|---|---|---|")
    for k, v in by_dataset.items():
        if v:
            lines.append(f"| {k} | {v['n']} | {v['hit1']:.3f} | {v['hit3']:.3f} | {v['hit5']:.3f} | "
                          f"{v['mrr']:.3f} | {v['ndcg3']:.3f} | {v['context_recall']:.3f} |")

    REPORT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nĐã ghi: {REPORT_MD}")
    print(f"Dữ liệu thô: {REPORT_JSON}")
    print("\n=== TỔNG THỂ ===")
    print(json.dumps(overall, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
