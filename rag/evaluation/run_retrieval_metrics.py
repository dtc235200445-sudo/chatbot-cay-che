"""
Đánh giá lại tầng truy xuất với bộ chỉ số đầy đủ (không gọi LLM):

  Context Precision@K  chunk lấy ra có liên quan không, có tính thứ tự (công thức RAGAS:
                       trung bình Precision@k tại các vị trí có chunk liên quan).
  Context Recall@K     top-K có đủ thông tin để trả lời không: tỉ lệ answer_key_points được
                       phủ bởi ít nhất một chunk trong top-K.
  Precision@K          số chunk liên quan trong top-K / K.
  Recall@K             số chunk liên quan trong top-K / tổng số chunk liên quan trong kho.
  MRR                  1 / vị trí của chunk liên quan đầu tiên.

Khác với nhãn "một chunk đúng" (source_chunk_id) của các lượt trước, tập chunk liên quan R(q)
được xác định lại từ answer_key_points: một chunk là liên quan nếu chứa nguyên văn (≥ KP_THRESHOLD
số bigram) ít nhất một ý chính của đáp án. Ý chính trong bộ 1000 câu được trích từ chunk nguồn nên
chunk nguồn luôn thuộc R(q); các chunk khác lặp lại cùng thông tin cũng được tính là liên quan.

Đây là phiên bản dựa trên nhãn. RAGAS gốc dùng LLM để chấm từng chunk; ở đây thay bằng so khớp văn
bản để chạy được trên toàn bộ câu hỏi, lặp lại được và không tốn chi phí.

Chạy: python -m rag.evaluation.run_retrieval_metrics
"""
import json
import re
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np

from rag.evaluation.robustness import swap_typos
from rag.evaluation.run_extended_evaluation import SYSTEMS, TEA, VANILLA, V2, Vanilla, tea_rank
from rag.evaluation.run_qa1000_retrieval import DATASET_PATH
from rag.retriever import RAGRetriever
from rag.text_utils import fold_diacritics, normalize_text
from rag.vector_store import VectorStoreManager

ROOT = Path(__file__).resolve().parent.parent.parent
REPORT_MD = ROOT / "docs" / "RAG_RETRIEVAL_METRICS.md"
REPORT_JSON = Path(__file__).resolve().parent / "retrieval_metrics_raw.json"
SHIFTED = Path(__file__).resolve().parent / "shifted_questions.json"
EVAL_SET = Path(__file__).with_name("eval_set.json")
TOP_K = 5
K_VALUES = (1, 3, 5)
MAIN_K = 3  # số chunk Tea AI đưa cho LLM
KP_THRESHOLD = 0.9
N_BOOT = 2000
SEED = 20260925
TEA_FULL = "Tea AI hybrid"


# ------------------------------------------------------------------ nhãn liên quan
def bigrams(text):
    w = re.findall(r"\w+", normalize_text(text))
    return {tuple(w[i:i + 2]) for i in range(len(w) - 1)} or {tuple(w)}


def covers(kp_ng, chunk_ng):
    return len(kp_ng & chunk_ng) / len(kp_ng) >= KP_THRESHOLD


def key_points(row):
    kps = row.get("answer_key_points") or []
    if isinstance(kps, str):
        try:
            kps = json.loads(kps)
        except json.JSONDecodeError:
            kps = [kps]
    return [k for k in kps if k.strip()]


# ------------------------------------------------------------------ chỉ số trên một câu
def per_query(ranked, relevant, kp_cover=None):
    """ranked: list chunk_id; relevant: set chunk_id; kp_cover: list[set chunk_id] — các chunk phủ từng ý chính."""
    out = {}
    v = [cid in relevant for cid in ranked]
    for k in K_VALUES:
        hits = sum(v[:k])
        out[f"precision@{k}"] = hits / k
        out[f"recall@{k}"] = hits / len(relevant) if relevant else 0.0
        out[f"hit@{k}"] = float(hits > 0)
        # Context Precision (RAGAS): sum_k P@k * v_k / (số chunk liên quan trong top-K)
        num = sum(sum(v[:i + 1]) / (i + 1) for i in range(k) if v[i])
        out[f"context_precision@{k}"] = num / hits if hits else 0.0
        if kp_cover is not None:
            top = set(ranked[:k])
            out[f"context_recall@{k}"] = sum(bool(c & top) for c in kp_cover) / len(kp_cover)
        else:  # không có ý chính: dùng Recall@K theo nhãn
            out[f"context_recall@{k}"] = out[f"recall@{k}"]
    first = next((i for i, x in enumerate(v) if x), None)
    out["mrr"] = 1.0 / (first + 1) if first is not None else 0.0
    return out


METRICS = [f"context_precision@{MAIN_K}", f"context_recall@{MAIN_K}", f"precision@{MAIN_K}", f"recall@{MAIN_K}", "mrr", f"hit@{MAIN_K}"]
FULL_METRICS = [f"{m}@{k}" for m in ("context_precision", "context_recall", "precision", "recall", "hit") for k in K_VALUES] + ["mrr"]


def evaluate(ranked_by_sys, cases):
    """cases: [{"relevant": set, "kp_cover": list[set] | None}] → {system: {"per": [...], "mean": {...}}}"""
    out = {}
    for s, ranked in ranked_by_sys.items():
        per = [per_query(r, c["relevant"], c.get("kp_cover")) for r, c in zip(ranked, cases)]
        out[s] = {"per": per, "mean": {m: float(np.mean([p[m] for p in per])) for m in FULL_METRICS}}
    return out


def bootstrap_diff(a, b, rng):
    a, b = np.asarray(a, float), np.asarray(b, float)
    idx = rng.integers(0, len(a), (N_BOOT, len(a)))
    diffs = a[idx].mean(1) - b[idx].mean(1)
    return float((a - b).mean()), float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))


# ------------------------------------------------------------------ chính
def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rng = np.random.default_rng(SEED)

    rows = [json.loads(l) for l in DATASET_PATH.open(encoding="utf-8")]
    # Loại 72 câu vùng trồng (không có trong kho vector) và 24 câu thiếu dữ liệu (không có chunk liên quan).
    rows = [r for r in rows if r["dataset"] != "Tea_Regions_Project_Config" and r["question_type"] != "insufficient_data"]
    rows = [r for r in rows if key_points(r)]
    chunks = json.loads((ROOT / "data" / "knowledge_base.json").read_text(encoding="utf-8"))
    chunk_ng = {c["chunk_id"]: bigrams(c["title"] + " " + c["content"]) for c in chunks}

    cases = []
    for r in rows:
        kp_cover = [{cid for cid, ng in chunk_ng.items() if covers(bigrams(k), ng)} | {r["source_chunk_id"]}
                    for k in key_points(r)]
        cases.append({"relevant": set().union(*kp_cover), "kp_cover": kp_cover})
    n_rel = Counter(min(len(c["relevant"]), 5) for c in cases)
    print(f"{len(rows)} câu | {len(chunks)} chunk | số chunk liên quan/câu: {sorted(n_rel.items())}", flush=True)

    tmp = Path(tempfile.mkdtemp(prefix="ret_metrics_"))
    shutil.copytree(ROOT / "database" / "chroma_db", tmp / "chroma_copy")
    tea = RAGRetriever(VectorStoreManager(persist_dir=str(tmp / "chroma_copy")))
    tea.load()
    cache = {}
    orig_enc = tea.vector_store.encode_query
    tea.vector_store.encode_query = lambda q: cache.setdefault(q, orig_enc(q))
    vanilla = {name: Vanilla(mid, chunks) for name, mid in VANILLA.items()}

    def rank_all(qs):
        out = {name: v.rank(qs) for name, v in vanilla.items()}
        for name, mode in TEA.items():
            out[name] = tea_rank(tea, mode, qs)
        return out

    questions = [r["question"] for r in rows]
    sets = {}
    variants = {
        "Câu gốc (có dấu)": questions,
        "Gõ không dấu": [fold_diacritics(q) for q in questions],
        "Gõ nhầm + không dấu": [swap_typos(fold_diacritics(q)) for q in questions],
    }
    for label, qs in variants.items():
        print("chạy:", label, flush=True)
        sets[label] = {"n": len(qs), "note": "nhãn từ ý chính", "res": evaluate(rank_all(qs), cases)}

    es = [q for q in json.loads(EVAL_SET.read_text(encoding="utf-8"))["queries"] if q["type"] == "in_domain"]
    print("chạy: bộ viết tay", flush=True)
    hand_cases = [{"relevant": set(q["relevant_chunk_ids"])} for q in es]
    sets["Viết tay (72 câu, người gán nhãn)"] = {"n": len(es), "note": "nhãn người gán, nhiều chunk/câu",
                                                 "res": evaluate(rank_all([q["query"] for q in es]), hand_cases)}

    if SHIFTED.exists():
        sq = [q for q in json.loads(SHIFTED.read_text(encoding="utf-8"))["questions"] if q["overlap"] <= 0.35]
        print("chạy: bộ diễn đạt lại", flush=True)
        sets[f"Diễn đạt lại ({len(sq)} câu)"] = {"n": len(sq), "note": "một chunk nguồn/câu, nhãn nhiễu",
                                                 "res": evaluate(rank_all([q["question"] for q in sq]),
                                                                 [{"relevant": {q["source_chunk_id"]}} for q in sq])}
    shutil.rmtree(tmp, ignore_errors=True)

    # Ý nghĩa thống kê: Tea AI so với RAG thường đa ngữ, trên từng bộ câu
    sig = {}
    for label, st in sets.items():
        a, b = st["res"][TEA_FULL]["per"], st["res"][V2]["per"]
        sig[label] = {m: bootstrap_diff([p[m] for p in a], [p[m] for p in b], rng) for m in METRICS}

    # Theo loại câu hỏi (bộ gốc)
    main_res = sets["Câu gốc (có dấu)"]["res"]
    qtypes = sorted({r["question_type"] for r in rows})
    by_type = {s: {qt: {m: float(np.mean([p[m] for p, r in zip(main_res[s]["per"], rows) if r["question_type"] == qt]))
                        for m in METRICS} for qt in qtypes} for s in SYSTEMS}
    type_n = Counter(r["question_type"] for r in rows)

    REPORT_JSON.write_text(json.dumps({
        "config": {"top_k": TOP_K, "main_k": MAIN_K, "kp_threshold": KP_THRESHOLD, "n_relevant_hist": dict(n_rel)},
        "sets": {l: {"n": st["n"], "mean": {s: st["res"][s]["mean"] for s in SYSTEMS}} for l, st in sets.items()},
        "significance_tea_vs_v2": sig, "by_type": by_type,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------ báo cáo
    K = MAIN_K
    L = ["# Đánh giá tầng truy xuất: Context Precision, Context Recall, Precision@K, Recall@K, MRR\n",
         f"Không gọi LLM. {len(chunks)} chunk. K = {K} (số chunk Tea AI đưa cho LLM) trừ khi ghi khác.\n",
         "## Cách xác định chunk liên quan\n",
         f"Mỗi câu trong bộ 1000 câu có danh sách ý chính (`answer_key_points`) trích từ tài liệu. Một chunk được coi là "
         f"**liên quan** nếu chứa ít nhất một ý chính (≥ {KP_THRESHOLD:.0%} số cặp từ liền kề của ý chính xuất hiện trong chunk). "
         f"Chunk nguồn luôn liên quan. Đánh giá trên **{len(rows)} câu** (bỏ 72 câu thuộc nguồn vùng trồng, gồm cả 24 câu thiếu dữ liệu, "
         "vì nguồn này không có trong kho vector).\n",
         "Số chunk liên quan mỗi câu: " + ", ".join(f"{'≥5' if k == 5 else k} chunk: {v} câu" for k, v in sorted(n_rel.items())) + ".\n",
         "| Chỉ số | Trả lời câu hỏi | Công thức |", "|---|---|---|",
         "| Context Precision@K | Chunk liên quan có nằm ở đầu danh sách không | Trung bình Precision@k tại các vị trí k có chunk liên quan |",
         "| Context Recall@K | Top-K có đủ ý để trả lời không | Số ý chính được phủ / tổng số ý chính |",
         "| Precision@K | Trong K chunk lấy ra, bao nhiêu chunk liên quan | Số chunk liên quan trong top-K / K |",
         "| Recall@K | Lấy được bao nhiêu phần trong các chunk liên quan | Số chunk liên quan trong top-K / tổng số chunk liên quan |",
         "| MRR | Chunk liên quan đầu tiên đứng ở vị trí nào | Trung bình 1 / vị trí (0 nếu không có trong top-5) |",
         "\nPrecision@K bị giới hạn trên bởi (số chunk liên quan / K): phần lớn câu chỉ có 1 chunk liên quan nên Precision@3 tối đa "
         "khoảng 0.33. Chỉ số này dùng để so sánh giữa các hệ thống, không đọc như tỉ lệ tuyệt đối.\n"]

    for label, st in sets.items():
        L.append(f"\n## {label}: {st['n']} câu ({st['note']})\n")
        L.append(f"| Hệ thống | Context Precision@{K} | Context Recall@{K} | Precision@{K} | Recall@{K} | MRR | Hit@{K} |")
        L.append("|---|---|---|---|---|---|---|")
        for s in SYSTEMS:
            m = st["res"][s]["mean"]
            L.append(f"| {s} | " + " | ".join(f"{m[x]:.3f}" for x in METRICS) + " |")
        d = sig[label]
        L.append(f"\nTea AI − RAG thường đa ngữ (khoảng tin cậy 95%, bootstrap {N_BOOT} lần): " + "; ".join(
            f"{x.split('@')[0].replace('_', ' ')} {d[x][0]:+.3f} [{d[x][1]:+.3f}, {d[x][2]:+.3f}]" for x in METRICS[:5]) + ".\n")

    L.append("\n## Theo K (câu gốc có dấu)\n")
    L.append("| Hệ thống | " + " | ".join(f"{n}@{k}" for n in ("CP", "CR", "P", "R") for k in K_VALUES) + " |")
    L.append("|---|" + "---|" * (4 * len(K_VALUES)))
    for s in SYSTEMS:
        m = main_res[s]["mean"]
        L.append(f"| {s} | " + " | ".join(f"{m[f'{n}@{k}']:.3f}" for n in ("context_precision", "context_recall", "precision", "recall")
                                          for k in K_VALUES) + " |")
    L.append("\nCP = Context Precision, CR = Context Recall, P = Precision, R = Recall.\n")

    L.append(f"\n## Theo loại câu hỏi (câu gốc, Context Precision@{K} / Context Recall@{K})\n")
    L.append("| Hệ thống | " + " | ".join(f"{qt} (n={type_n[qt]})" for qt in qtypes) + " |")
    L.append("|---|" + "---|" * len(qtypes))
    for s in SYSTEMS:
        L.append(f"| {s} | " + " | ".join(f"{by_type[s][qt][METRICS[0]]:.2f} / {by_type[s][qt][METRICS[1]]:.2f}" for qt in qtypes) + " |")

    L.append("\n## Lưu ý khi diễn giải\n")
    L.append("- Liên quan được xác định bằng so khớp văn bản với ý chính, không phải LLM chấm như RAGAS gốc. Chunk diễn đạt cùng ý bằng "
             "từ ngữ khác sẽ không được tính là liên quan, nên Context Precision/Recall là cận dưới.")
    L.append("- Bộ viết tay và bộ diễn đạt lại không có ý chính; Context Recall ở hai bộ này bằng Recall@K theo nhãn chunk.")
    L.append("- Bộ diễn đạt lại chỉ có một chunk nguồn mỗi câu và còn nhãn nhiễu (xem RAG_EXTENDED_EVALUATION.md).")
    L.append("- Tea AI được hiệu chỉnh trên bộ viết tay nên số của Tea AI ở bộ này có thể lạc quan.")
    REPORT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))
    print(f"\nĐã ghi {REPORT_MD}")


if __name__ == "__main__":
    main()
