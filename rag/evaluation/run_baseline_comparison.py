"""
So sánh retrieval của Tea AI với các dạng "RAG thường" trên bộ 1000 câu hỏi (E:/NHÁP 2).

Cùng một kho tri thức (data/knowledge_base.json), cùng bộ câu hỏi, cùng top-k; chỉ khác cách truy xuất.
KHÔNG gọi LLM, KHÔNG ghi vào ChromaDB thật (đọc từ bản sao trong thư mục tạm).

Chạy: python -m rag.evaluation.run_baseline_comparison
"""
import json
import random
import shutil
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np

from rag import config
from rag.evaluation.run_qa1000_retrieval import DATASET_PATH, dcg_at_k
from rag.retriever import MODE_BM25, MODE_DENSE, MODE_HYBRID, RAGRetriever
from rag.text_utils import fold_diacritics
from rag.vector_store import VectorStoreManager

ROOT = Path(__file__).resolve().parent.parent.parent
REPORT_MD = ROOT / "docs" / "RAG_BASELINE_COMPARISON.md"
REPORT_JSON = Path(__file__).resolve().parent / "baseline_comparison_raw.json"
EVAL_SET = Path(__file__).with_name("eval_set.json")
TOP_K = 5
N_BOOT = 2000
SEED = 20260924

VANILLA_MODELS = {
    "V1 RAG thường (all-MiniLM-L6-v2, dense)": "sentence-transformers/all-MiniLM-L6-v2",
    "V2 RAG thường đa ngữ (paraphrase-multilingual-MiniLM, dense)": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
}
TEA_SYSTEMS = {
    "T1 + embedding tiếng Việt (bkai, dense)": MODE_DENSE,
    "T2 BM25 tiếng Việt (từ đơn + bigram, bỏ dấu)": MODE_BM25,
    "T3 Tea AI hybrid đầy đủ (bkai + BM25 + chỉ mục bỏ dấu)": MODE_HYBRID,
}


def load_questions():
    rows = [json.loads(l) for l in DATASET_PATH.open(encoding="utf-8")]
    return [r for r in rows if r["dataset"] != "Tea_Regions_Project_Config"]


def rank_of(ranked_ids, true_id):
    return ranked_ids.index(true_id) + 1 if true_id in ranked_ids else None


def summarize(ranks):
    n = len(ranks)
    return {
        "n": n,
        "hit1": sum(r == 1 for r in ranks) / n,
        "hit3": sum(r is not None and r <= 3 for r in ranks) / n,
        "hit5": sum(r is not None and r <= 5 for r in ranks) / n,
        "mrr": sum((1 / r) if r else 0.0 for r in ranks) / n,
        "ndcg3": sum(dcg_at_k(r, 3) for r in ranks) / n,
    }


def vanilla_ranks(model_name, chunks, questions):
    """RAG thường: embedding gốc của chunk (chỉ nội dung, không thêm tiêu đề, không tách từ), cosine, top-k."""
    from sentence_transformers import SentenceTransformer

    model = SentenceTransformer(model_name)
    doc_vecs = model.encode([c["content"] for c in chunks], normalize_embeddings=True, show_progress_bar=False)
    ids = [c["chunk_id"] for c in chunks]
    out = {}
    for label, qs in questions.items():
        q_vecs = model.encode(qs, normalize_embeddings=True, show_progress_bar=False, batch_size=64)
        sims = q_vecs @ doc_vecs.T
        out[label] = [list(np.array(ids)[np.argsort(-s)[:TOP_K]]) for s in sims]
    return out


def tea_ranks(retriever, mode, questions):
    out = {}
    for label, qs in questions.items():
        out[label] = [[c["chunk_id"] for c in retriever.retrieve(q, top_k=TOP_K, mode=mode)["retrieved_chunks"]] for q in qs]
    return out


def bootstrap_diff(a_hits, b_hits, rng):
    """Chênh lệch trung bình (a - b) và khoảng tin cậy 95% bằng bootstrap ghép cặp."""
    a, b = np.asarray(a_hits, float), np.asarray(b_hits, float)
    diffs = []
    n = len(a)
    for _ in range(N_BOOT):
        idx = rng.integers(0, n, n)
        diffs.append(a[idx].mean() - b[idx].mean())
    return float((a - b).mean()), float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


def mcnemar_exact_p(a_hits, b_hits):
    from math import comb

    a, b = np.asarray(a_hits, bool), np.asarray(b_hits, bool)
    n01, n10 = int((~a & b).sum()), int((a & ~b).sum())
    n = n01 + n10
    if n == 0:
        return 1.0
    k = min(n01, n10)
    p = sum(comb(n, i) for i in range(0, k + 1)) / (2 ** n) * 2
    return min(1.0, p)


def evaluate_gate(retriever, models_vanilla):
    queries = json.loads(EVAL_SET.read_text(encoding="utf-8"))["queries"]
    in_q = [q for q in queries if q["type"] == "in_domain"]
    out_q = [q for q in queries if q["type"] != "in_domain"]
    acc_in = sum(retriever.retrieve(q["query"], top_k=config.DEFAULT_TOP_K)["is_relevant"] for q in in_q)
    rej_out = sum(not retriever.retrieve(q["query"], top_k=config.DEFAULT_TOP_K)["is_relevant"] for q in out_q)
    return {"n_in": len(in_q), "n_out": len(out_q), "tea_accept_in": acc_in / len(in_q), "tea_reject_out": rej_out / len(out_q)}


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rng = np.random.default_rng(SEED)
    random.seed(SEED)

    rows = load_questions()
    chunks = json.loads((ROOT / "data" / "knowledge_base.json").read_text(encoding="utf-8"))
    questions = {
        "có dấu": [r["question"] for r in rows],
        "không dấu": [fold_diacritics(r["question"]) for r in rows],
    }
    true_ids = [r["source_chunk_id"] for r in rows]
    print(f"{len(rows)} câu hỏi | {len(chunks)} chunk | top_k={TOP_K}")

    tmp = Path(tempfile.mkdtemp(prefix="chroma_copy_"))
    shutil.copytree(ROOT / "database" / "chroma_db", tmp / "chroma_db")
    retriever = RAGRetriever(VectorStoreManager(persist_dir=str(tmp / "chroma_db")))
    retriever.load()

    # Dùng lại vector của cùng một câu hỏi giữa các chế độ dense/bm25/hybrid (tiết kiệm thời gian, không đổi kết quả)
    orig_encode = retriever.vector_store.encode_query
    cache = {}

    def cached_encode(q):
        if q not in cache:
            cache[q] = orig_encode(q)
        return cache[q]

    retriever.vector_store.encode_query = cached_encode

    all_ranked = {}  # system -> label -> list[list[id]]
    for name, model_name in VANILLA_MODELS.items():
        print("chạy:", name, flush=True)
        all_ranked[name] = vanilla_ranks(model_name, chunks, questions)
    for name, mode in TEA_SYSTEMS.items():
        print("chạy:", name, flush=True)
        all_ranked[name] = tea_ranks(retriever, mode, questions)

    gate = evaluate_gate(retriever, VANILLA_MODELS)
    shutil.rmtree(tmp, ignore_errors=True)

    systems = list(all_ranked)
    ranks = {s: {lab: [rank_of(r, t) for r, t in zip(all_ranked[s][lab], true_ids)] for lab in questions} for s in systems}

    overall = {s: summarize(ranks[s]["có dấu"]) for s in systems}
    unaccented = {s: summarize(ranks[s]["không dấu"]) for s in systems}

    qtypes = sorted({r["question_type"] for r in rows})
    by_type = {
        s: {qt: summarize([rk for rk, r in zip(ranks[s]["có dấu"], rows) if r["question_type"] == qt]) for qt in qtypes}
        for s in systems
    }
    datasets = sorted({r["dataset"] for r in rows})
    by_dataset = {
        s: {d: summarize([rk for rk, r in zip(ranks[s]["có dấu"], rows) if r["dataset"] == d]) for d in datasets}
        for s in systems
    }

    full = "T3 Tea AI hybrid đầy đủ (bkai + BM25 + chỉ mục bỏ dấu)"
    sig = {}
    for base in [s for s in systems if s != full]:
        for lab in questions:
            fh = [r is not None and r <= 3 for r in ranks[full][lab]]
            bh = [r is not None and r <= 3 for r in ranks[base][lab]]
            d, lo, hi = bootstrap_diff(fh, bh, rng)
            sig[f"{base}|{lab}"] = {"diff_hit3": d, "ci95": [lo, hi], "mcnemar_p": mcnemar_exact_p(fh, bh)}

    REPORT_JSON.write_text(
        json.dumps({"overall": overall, "unaccented": unaccented, "by_type": by_type, "by_dataset": by_dataset,
                    "gate": gate, "significance": sig}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    L = []
    L.append("# So sánh Tea AI với RAG thường (tầng truy xuất)\n")
    L.append(f"Bộ câu hỏi: `{DATASET_PATH}` — **{len(rows)} câu thuộc phạm vi RAG** (đã loại 72 câu `Tea_Regions_Project_Config`, "
             f"nguồn này không nằm trong kho vector). Cùng {len(chunks)} chunk của `data/knowledge_base.json`, top-{TOP_K}, "
             "không gọi LLM. Nhãn đúng = `source_chunk_id`.\n")
    L.append("**Các hệ thống** (xếp từ RAG thường nhất đến Tea AI đầy đủ; mỗi bước thêm một thành phần):\n")
    for s in systems:
        L.append(f"- {s}")
    L.append("\nRAG thường (V1, V2): embed nội dung chunk nguyên trạng bằng model có sẵn, cosine, lấy top-k, không có BM25, "
             "không ghép tiêu đề, không tách từ tiếng Việt, không chỉ mục bỏ dấu, không cổng từ chối.\n")

    def table(title, data, note=""):
        L.append(f"\n## {title}\n")
        if note:
            L.append(note + "\n")
        L.append("| Hệ thống | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 |")
        L.append("|---|---|---|---|---|---|")
        for s in systems:
            m = data[s]
            L.append(f"| {s} | {m['hit1']:.3f} | {m['hit3']:.3f} | {m['hit5']:.3f} | {m['mrr']:.3f} | {m['ndcg3']:.3f} |")

    table(f"1. Tổng thể ({len(rows)} câu, gõ có dấu)", overall)
    table("2. Câu hỏi gõ không dấu (cùng câu, bỏ dấu tiếng Việt)", unaccented,
          "Người dùng thật thường gõ không dấu; RAG thường không có xử lý riêng cho trường hợp này.")

    L.append("\n## 3. Theo loại câu hỏi (Hit@3 / MRR)\n")
    L.append("| Hệ thống | " + " | ".join(qtypes) + " |")
    L.append("|---|" + "---|" * len(qtypes))
    for s in systems:
        L.append(f"| {s} | " + " | ".join(f"{by_type[s][qt]['hit3']:.3f} / {by_type[s][qt]['mrr']:.3f}" for qt in qtypes) + " |")

    L.append("\n## 4. Theo nguồn tài liệu (Hit@3 / MRR)\n")
    L.append("| Hệ thống | " + " | ".join(f"{d} (n={by_dataset[systems[0]][d]['n']})" for d in datasets) + " |")
    L.append("|---|" + "---|" * len(datasets))
    for s in systems:
        L.append(f"| {s} | " + " | ".join(f"{by_dataset[s][d]['hit3']:.3f} / {by_dataset[s][d]['mrr']:.3f}" for d in datasets) + " |")

    L.append("\n## 5. Cổng từ chối câu hỏi ngoài cơ sở tri thức\n")
    L.append(f"Bộ `rag/evaluation/eval_set.json`: {gate['n_in']} câu trong phạm vi, {gate['n_out']} câu ngoài phạm vi/thiếu tri thức.\n")
    L.append("| Hệ thống | Nhận đúng câu trong phạm vi | Từ chối đúng câu ngoài phạm vi |")
    L.append("|---|---|---|")
    for s in systems[:2]:
        L.append(f"| {s} | 100.0% (không có cổng, luôn trả top-k) | 0.0% |")
    L.append(f"| Tea AI (cổng cosine + BM25, cấu hình hiện tại) | {gate['tea_accept_in']:.1%} | {gate['tea_reject_out']:.1%} |")

    L.append("\n## 6. Ý nghĩa thống kê: Tea AI đầy đủ (T3) so với từng hệ thống, Hit@3\n")
    L.append(f"Bootstrap ghép cặp {N_BOOT} lần, kiểm định McNemar chính xác (hai phía).\n")
    L.append("| So với | Loại câu | Chênh Hit@3 (T3 − hệ thống đó) | KTC 95% | p (McNemar) |")
    L.append("|---|---|---|---|---|")
    for key, v in sig.items():
        base, lab = key.split("|")
        L.append(f"| {base} | {lab} | {v['diff_hit3']:+.3f} | [{v['ci95'][0]:+.3f}, {v['ci95'][1]:+.3f}] | {v['mcnemar_p']:.2g} |")

    L.append("\n## Lưu ý khi diễn giải\n")
    L.append("- Kho tri thức đã được chia chunk sẵn (171 chunk), nên so sánh này **không** đo ảnh hưởng của chiến lược chunking.")
    L.append("- Bộ câu hỏi được sinh từ chính các chunk nguồn, nhiều câu là paraphrase của cùng một chunk; nhãn đúng là đúng một chunk, "
             "nên số liệu có thể thấp hơn thực tế nếu nhiều chunk cùng chứa đáp án.")
    L.append("- Siêu tham số của Tea AI (alpha, ngưỡng cổng) được hiệu chỉnh trên `eval_set.json`, không phải trên bộ 1000 câu này.")
    L.append("- Đây là đánh giá tầng truy xuất. Chất lượng câu trả lời cuối cùng do LLM sinh ra được đo riêng (xem `QA1000_ANSWER_RESULTS.md`).")
    REPORT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\nĐã ghi {REPORT_MD}")


if __name__ == "__main__":
    main()
