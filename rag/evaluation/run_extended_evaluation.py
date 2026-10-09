"""
Đánh giá mở rộng tầng truy xuất (không gọi LLM) để khắc phục các hạn chế của lượt so sánh đầu:

 1. Nhãn đúng chỉ là một chunk  -> thêm nhãn NỚI LỎNG: top-k có phủ nội dung chunk nguồn không (độc lập ranh giới chunk).
 2. Câu hỏi sinh từ chính chunk -> bộ câu hỏi viết tay (eval_set.json) và bộ câu hỏi "lệch từ vựng" (gen_shifted_questions.py).
 3. Độ bền                     -> gõ nhầm, gõ nhầm + không dấu.
 4. Độ trễ                     -> đo riêng độ trễ truy xuất (ms) của từng hệ thống, không lẫn độ trễ LLM.
 5. Chiến lược chunking        -> chia lại kho bằng cửa sổ cố định (50/100/200 từ) và so sánh.

Chạy: python -m rag.evaluation.run_extended_evaluation
"""
import json
import math
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import numpy as np

from rag import config
from rag.bm25 import BM25Index
from rag.evaluation.metrics import summarize_ranking
from rag.evaluation.robustness import swap_typos
from rag.evaluation.run_qa1000_retrieval import DATASET_PATH
from rag.retriever import MODE_BM25, MODE_DENSE, MODE_HYBRID, RAGRetriever
from rag.text_utils import build_bm25_text, build_index_text, fold_diacritics, normalize_text, tokenize
from rag.vector_store import IndexSnapshot, VectorStoreManager

ROOT = Path(__file__).resolve().parent.parent.parent
REPORT_MD = ROOT / "docs" / "RAG_EXTENDED_EVALUATION.md"
REPORT_JSON = Path(__file__).resolve().parent / "extended_evaluation_raw.json"
SHIFTED = Path(__file__).resolve().parent / "shifted_questions.json"
EVAL_SET = Path(__file__).with_name("eval_set.json")
TOP_K = 5
COVER_THRESHOLD = 0.5

V1, V2 = "all-MiniLM-L6-v2", "paraphrase-multilingual-MiniLM"
VANILLA = {V1: "sentence-transformers/all-MiniLM-L6-v2", V2: "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"}
TEA = {"bkai dense": MODE_DENSE, "BM25 tiếng Việt": MODE_BM25, "Tea AI hybrid": MODE_HYBRID}
SYSTEMS = [V1, V2, *TEA]


# ------------------------------------------------------------------ tiện ích
def ngrams(text, n=4):
    words = re.findall(r"\w+", normalize_text(text))
    return {tuple(words[i:i + n]) for i in range(len(words) - n + 1)} or {tuple(words)}


def coverage(ref_ng, texts):
    union = set()
    for t in texts:
        union |= ngrams(t)
    return len(ref_ng & union) / len(ref_ng) if ref_ng else 0.0


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h


def fmt_ci(k, n):
    lo, hi = wilson(k, n)
    return f"{k / n:.3f} [{lo:.2f}-{hi:.2f}]"


class Vanilla:
    """RAG thường: embed nội dung chunk nguyên trạng, cosine, top-k."""

    def __init__(self, model_name, chunks):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(model_name)
        self.ids = np.array([c["chunk_id"] for c in chunks])
        self.vecs = self.model.encode([c["content"] for c in chunks], normalize_embeddings=True, show_progress_bar=False)

    def rank(self, questions, k=TOP_K):
        q = self.model.encode(questions, normalize_embeddings=True, show_progress_bar=False, batch_size=64)
        return [list(self.ids[np.argsort(-s)[:k]]) for s in q @ self.vecs.T]


def build_tea(chunks, tmpdir):
    """Dựng RAGRetriever của Tea AI trên một danh sách chunk bất kỳ (không ghi vào ChromaDB thật)."""
    vs = VectorStoreManager(persist_dir=str(tmpdir))
    eng = vs._engine()
    texts = [build_index_text(c["title"], c["content"]) for c in chunks]
    snap = IndexSnapshot(
        ids=[c["chunk_id"] for c in chunks],
        documents=[c["content"] for c in chunks],
        metadatas=[{"title": c["title"], "source": c.get("source", ""), "section": "", "page": -1} for c in chunks],
        embeddings=eng.encode(texts),
        embeddings_folded=eng.encode([fold_diacritics(t) for t in texts]),
    )
    r = RAGRetriever(vs)
    r._snapshot = snap
    r._bm25 = BM25Index(
        [tokenize(build_bm25_text(m["title"], d, config.BM25_TITLE_BOOST)) for d, m in zip(snap.documents, snap.metadatas)],
        k1=config.BM25_K1, b=config.BM25_B,
    )
    return r


def tea_rank(retriever, mode, questions, k=TOP_K):
    return [[c["chunk_id"] for c in retriever.retrieve(q, top_k=k, mode=mode)["retrieved_chunks"]] for q in questions]


def rechunk(chunks, size, overlap):
    """Chia lại kho bằng cửa sổ cố định theo số từ trên văn bản từng tài liệu (tiêu đề chunk = tên tài liệu)."""
    docs = {}
    for c in sorted(chunks, key=lambda c: c["chunk_id"]):
        docs.setdefault(c["source"], []).append(c["content"])
    out = []
    for source, parts in docs.items():
        words = " ".join(parts).split()
        step = size - overlap
        for i in range(0, max(1, len(words) - overlap), step):
            window = words[i:i + size]
            if len(window) < 15 and out and out[-1]["source"] == source:
                break
            out.append({"chunk_id": f"w{size}_{len(out):04d}", "title": source, "source": source, "content": " ".join(window)})
    return out


def strict_hits(ranked, true_ids, k):
    return [t in r[:k] for r, t in zip(ranked, true_ids)]


def relaxed_hits(ranked, ref_ngs, text_of, k):
    return [coverage(ng, [text_of[i] for i in r[:k]]) >= COVER_THRESHOLD for r, ng in zip(ranked, ref_ngs)]


# ------------------------------------------------------------------ chính
def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = [json.loads(l) for l in DATASET_PATH.open(encoding="utf-8")]
    rows = [r for r in rows if r["dataset"] != "Tea_Regions_Project_Config"]
    chunks = json.loads((ROOT / "data" / "knowledge_base.json").read_text(encoding="utf-8"))
    text_of = {c["chunk_id"]: c["content"] for c in chunks}
    questions = [r["question"] for r in rows]
    true_ids = [r["source_chunk_id"] for r in rows]
    ref_ng = [ngrams(r["reference_context"]) for r in rows]
    print(f"{len(rows)} câu | {len(chunks)} chunk", flush=True)

    tmp = Path(tempfile.mkdtemp(prefix="ext_eval_"))
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

    R = {}
    result = {}

    # ---- 1. nhãn chặt vs nhãn nới lỏng + mức nhập nhằng của nhãn
    print("1. nhãn nới lỏng", flush=True)
    R["orig"] = rank_all(questions)
    other_cover = 0
    for r, ng in zip(rows, ref_ng):
        if any(coverage(ng, [c["content"]]) >= COVER_THRESHOLD for c in chunks if c["chunk_id"] != r["source_chunk_id"]):
            other_cover += 1
    result["label_ambiguity"] = {"n": len(rows), "another_chunk_covers": other_cover}
    result["relaxed"] = {
        s: {
            "strict_hit3": sum(strict_hits(R["orig"][s], true_ids, 3)), "relaxed_hit3": sum(relaxed_hits(R["orig"][s], ref_ng, text_of, 3)),
            "strict_hit1": sum(strict_hits(R["orig"][s], true_ids, 1)), "relaxed_hit1": sum(relaxed_hits(R["orig"][s], ref_ng, text_of, 1)),
            "n": len(rows),
        } for s in SYSTEMS
    }

    # ---- 2a. bộ viết tay
    print("2a. bộ viết tay", flush=True)
    es = json.loads(EVAL_SET.read_text(encoding="utf-8"))["queries"]
    in_dom = [q for q in es if q["type"] == "in_domain"]
    ranked_hand = rank_all([q["query"] for q in in_dom])
    result["hand"] = {
        s: summarize_ranking([{"ranked_ids": r, "relevant": set(q["relevant_chunk_ids"])} for r, q in zip(ranked_hand[s], in_dom)])
        for s in SYSTEMS
    }
    result["hand_n"] = len(in_dom)

    # ---- 2b. bộ lệch từ vựng (lọc chặt theo độ trùng từ với chunk nguồn)
    result["shifted"] = None
    if SHIFTED.exists():
        sh = json.loads(SHIFTED.read_text(encoding="utf-8"))
        sq_all = sh.get("questions") or []
        result["shifted"] = {"summary": sh.get("summary"), "sets": {}}
        for label, th in (("trùng từ ≤ 0.35", 0.35), ("trùng từ ≤ 0.20 (rất lệch)", 0.20)):
            sq = [q for q in sq_all if q["overlap"] <= th]
            if not sq:
                continue
            print(f"2b. bộ lệch từ vựng {label} ({len(sq)} câu)", flush=True)
            ranked_sh = rank_all([q["question"] for q in sq])
            sh_true = [q["source_chunk_id"] for q in sq]
            result["shifted"]["sets"][label] = {
                "n": len(sq), "mean_overlap": float(np.mean([q["overlap"] for q in sq])),
                "n_chunks": len({q["source_chunk_id"] for q in sq}),
                "per_system": {s: {"hit1": sum(strict_hits(ranked_sh[s], sh_true, 1)), "hit3": sum(strict_hits(ranked_sh[s], sh_true, 3)),
                                   "hit5": sum(strict_hits(ranked_sh[s], sh_true, 5)),
                                   "mrr": float(np.mean([(1 / (r.index(t) + 1)) if t in r else 0.0 for r, t in zip(ranked_sh[s], sh_true)]))}
                               for s in SYSTEMS},
            }

    # ---- 3. gõ nhầm
    print("3. gõ nhầm", flush=True)
    variants = {"gõ nhầm (có dấu)": [swap_typos(q) for q in questions],
                "gõ nhầm + không dấu": [swap_typos(fold_diacritics(q)) for q in questions]}
    result["typo"] = {}
    for label, qs in variants.items():
        ranked = rank_all(qs)
        result["typo"][label] = {s: {"hit3": sum(strict_hits(ranked[s], true_ids, 3)), "n": len(qs)} for s in SYSTEMS}

    # ---- 4. độ trễ truy xuất (không dùng cache)
    print("4. độ trễ", flush=True)
    fresh = RAGRetriever(VectorStoreManager(persist_dir=str(tmp / "chroma_copy")))
    fresh.load()
    sample = questions[::9][:100]
    lat = {}
    for name, v in vanilla.items():
        v.rank(sample[:3])
        t = []
        for q in sample:
            s = time.perf_counter(); v.rank([q]); t.append((time.perf_counter() - s) * 1000)
        lat[name] = t
    for name, mode in TEA.items():
        tea_rank(fresh, mode, sample[:3])
        t = []
        for q in sample:
            s = time.perf_counter(); fresh.retrieve(q, top_k=TOP_K, mode=mode); t.append((time.perf_counter() - s) * 1000)
        lat[name] = t
    result["latency_ms"] = {s: {"median": float(np.median(v)), "p95": float(np.percentile(v, 95))} for s, v in lat.items()}

    # ---- 5. chunking
    print("5. chunking", flush=True)
    chunking = {}
    corpora = {"gốc (theo mục, ~95 từ/chunk)": chunks}
    for size, ov in ((50, 10), (100, 20), (200, 40)):
        corpora[f"cố định {size} từ (chồng {ov})"] = rechunk(chunks, size, ov)
    for label, corpus in corpora.items():
        toc = {c["chunk_id"]: c["content"] for c in corpus}
        ck_tea = build_tea(corpus, tmp / f"c_{abs(hash(label)) % 10**6}")
        ck_van = Vanilla(VANILLA[V2], corpus)
        for sysname, ranked in ((V2, ck_van.rank(questions, 3)), ("Tea AI hybrid", tea_rank(ck_tea, MODE_HYBRID, questions, 3))):
            hits = relaxed_hits(ranked, ref_ng, toc, 3)
            words = float(np.mean([sum(len(toc[i].split()) for i in r) for r in ranked]))
            chunking[f"{label}|{sysname}"] = {"n_chunks": len(corpus), "relaxed_hit3": sum(hits), "n": len(questions), "context_words": words}
        print("  ", label, len(corpus), "chunk", flush=True)
    result["chunking"] = chunking

    shutil.rmtree(tmp, ignore_errors=True)
    REPORT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    write_report(result)


def write_report(res):
    L = ["# Đánh giá mở rộng tầng truy xuất (khắc phục các hạn chế của lượt so sánh đầu)\n",
         "Không gọi LLM. Cùng 171 chunk, cùng 928 câu trong phạm vi RAG (trừ khi nêu khác). Khoảng trong ngoặc vuông là khoảng tin cậy Wilson 95%.\n"]

    n = res["label_ambiguity"]["n"]
    L.append("## 1. Nhãn đúng chỉ là một chunk: nhãn chặt và nhãn nới lỏng\n")
    L.append(f"Nhãn chặt: top-k phải chứa đúng `source_chunk_id`. Nhãn nới lỏng: các chunk trong top-k **phủ ít nhất {int(COVER_THRESHOLD*100)}%** "
             "các cụm 4 từ của đoạn nguồn, không phụ thuộc chunk nào chứa nội dung đó.\n")
    L.append(f"Mức nhập nhằng của nhãn: **{res['label_ambiguity']['another_chunk_covers']}/{n} câu** có một chunk KHÁC cũng phủ ≥{int(COVER_THRESHOLD*100)}% đoạn nguồn.\n")
    L.append("| Hệ thống | Hit@3 chặt | Hit@3 nới lỏng | Hit@1 chặt | Hit@1 nới lỏng |")
    L.append("|---|---|---|---|---|")
    for s in SYSTEMS:
        r = res["relaxed"][s]
        L.append(f"| {s} | {fmt_ci(r['strict_hit3'], n)} | {fmt_ci(r['relaxed_hit3'], n)} | {fmt_ci(r['strict_hit1'], n)} | {fmt_ci(r['relaxed_hit1'], n)} |")

    L.append("\n## 2. Câu hỏi không sinh từ chính chunk\n")
    L.append(f"### 2a. Bộ viết tay (`eval_set.json`, {res['hand_n']} câu trong phạm vi, nhãn do người gán)\n")
    L.append("Lưu ý: siêu tham số của Tea AI (alpha, ngưỡng cổng) được hiệu chỉnh trên chính bộ này nên số của Tea AI có thể lạc quan; các hệ thống RAG thường không bị ảnh hưởng.\n")
    L.append("| Hệ thống | Hit@1 | Hit@3 | Hit@5 | MRR |")
    L.append("|---|---|---|---|---|")
    for s in SYSTEMS:
        m = res["hand"][s]
        L.append(f"| {s} | {m['hit@1']:.3f} | {m['hit@3']:.3f} | {m['hit@5']:.3f} | {m['mrr']:.3f} |")

    sh = res.get("shifted")
    L.append("\n### 2b. Bộ câu hỏi lệch từ vựng (LLM viết lại bằng lời đời thường, không chép thuật ngữ của chunk)\n")
    if sh and sh["sets"]:
        sm = sh["summary"]
        L.append(f"Model sinh `{sm['model']}`; {sm['n_generated']} câu sinh ra từ {sm['n_chunks']} chunk. Độ trùng từ nội dung giữa câu hỏi và chunk nguồn: "
                 f"bộ 928 câu gốc trung bình **{sm['mean_overlap_original_928']:.2f}**, câu mới sinh chưa lọc **{sm['mean_overlap_generated']:.2f}** "
                 "(LLM chưa tự tránh được từ ngữ tài liệu nên phải lọc thêm). Bộ lọc ≤ 0.5 ban đầu KHÔNG làm câu hỏi lệch hơn bộ gốc, "
                 "vì vậy dùng hai tập con lọc chặt hơn:\n")
        for label, st_ in sh["sets"].items():
            L.append(f"**Tập {label}**: {st_['n']} câu từ {st_['n_chunks']} chunk, độ trùng từ trung bình {st_['mean_overlap']:.2f}.\n")
            L.append("| Hệ thống | Hit@1 | Hit@3 | Hit@5 | MRR |")
            L.append("|---|---|---|---|---|")
            for s_ in SYSTEMS:
                m = st_["per_system"][s_]
                L.append(f"| {s_} | {fmt_ci(m['hit1'], st_['n'])} | {fmt_ci(m['hit3'], st_['n'])} | {fmt_ci(m['hit5'], st_['n'])} | {m['mrr']:.3f} |")
            L.append("")
    else:
        L.append("_Chưa có bộ câu hỏi lệch từ vựng._")

    L.append("\n## 3. Độ bền khi người dùng gõ nhầm (Hit@3 chặt, 928 câu)\n")
    L.append("| Hệ thống | " + " | ".join(res["typo"]) + " |")
    L.append("|---|" + "---|" * len(res["typo"]))
    for s in SYSTEMS:
        L.append(f"| {s} | " + " | ".join(fmt_ci(res['typo'][v][s]['hit3'], res['typo'][v][s]['n']) for v in res["typo"]) + " |")

    L.append("\n## 4. Độ trễ truy xuất (ms/câu, chạy trên CPU, không có LLM; 100 câu, bỏ 3 lượt khởi động)\n")
    L.append("| Hệ thống | Trung vị | P95 |")
    L.append("|---|---|---|")
    for s in SYSTEMS:
        m = res["latency_ms"][s]
        L.append(f"| {s} | {m['median']:.1f} | {m['p95']:.1f} |")

    L.append("\n## 5. Ảnh hưởng của chiến lược chunking (nhãn nới lỏng, Hit@3, 928 câu)\n")
    L.append("Chia lại cùng văn bản bằng cửa sổ cố định theo số từ; tiêu đề chunk = tên tài liệu (mất tiêu đề theo mục). "
             "\"Từ ngữ cảnh\" = số từ trung bình của top-3 chunk đưa cho LLM (chi phí prompt).\n")
    L.append("| Cách chia | Số chunk | Hệ thống | Hit@3 nới lỏng | Từ ngữ cảnh TB |")
    L.append("|---|---|---|---|---|")
    for key, v in res["chunking"].items():
        label, sysname = key.split("|")
        L.append(f"| {label} | {v['n_chunks']} | {sysname} | {fmt_ci(v['relaxed_hit3'], v['n'])} | {v['context_words']:.0f} |")
    REPORT_MD.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    main()
