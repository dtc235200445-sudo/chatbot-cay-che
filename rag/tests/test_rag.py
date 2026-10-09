"""
Test cho pipeline RAG.

- Nhóm "unit": thuần Python, chạy tức thì (tokenizer, BM25, metrics).
- Nhóm "index": dùng chỉ mục ChromaDB thật (cần `python -m rag.ingest` trước) làm test hồi quy chất lượng,
  với ngưỡng thấp hơn số đo thực tế một khoảng an toàn để chỉ báo động khi chất lượng tụt rõ rệt.
"""
import unicodedata

import pytest

from rag.bm25 import BM25Index
from rag.evaluation.metrics import hit_at_k, ndcg_at_k, precision_at_k, reciprocal_rank, summarize_ranking
from rag.evaluation.run_eval import evaluate_gate, evaluate_ranking, load_eval_set
from rag.ingest import chunk_to_record
from rag.retriever import MODE_BM25, MODE_DENSE, MODE_HYBRID, RAGRetriever
from rag.text_utils import build_index_text, min_max, tokenize


# ---------------------------------------------------------------- unit
def test_tokenize_keeps_domain_bigrams_and_drops_stopwords():
    tokens = tokenize("Bệnh thối búp trên cây chè là gì?")
    # Token đã bỏ dấu để câu gõ không dấu vẫn khớp
    assert "thoi" in tokens and "bup" in tokens
    assert "thoi_bup" in tokens
    assert "la" not in tokens and "gi" not in tokens


def test_tokenize_is_diacritic_insensitive():
    assert tokenize("Bệnh thối búp") == tokenize("benh thoi bup")
    assert tokenize("Đà Lạt") == tokenize("da lat")


def test_stopwords_are_matched_before_folding():
    """"cỏ" không được bị coi là từ dừng "có" chỉ vì giống nhau khi bỏ dấu."""
    assert "co" in tokenize("làm cỏ")
    assert "co" not in tokenize("có thể")


def test_is_unaccented():
    from rag.text_utils import is_unaccented
    assert is_unaccented("benh thoi bup tren cay che")
    assert not is_unaccented("bệnh thối búp")
    assert not is_unaccented("benh thối bup")  # gõ lẫn: coi là có dấu
    assert not is_unaccented("12345")


def test_tokenize_normalizes_unicode_and_case():
    composed = unicodedata.normalize("NFC", "Nhện đỏ")
    decomposed = unicodedata.normalize("NFD", "Nhện đỏ")
    assert composed != decomposed  # hai dạng mã hóa khác nhau về byte
    assert tokenize(composed) == tokenize(decomposed)


def test_bm25_ranks_matching_document_first_and_ignores_unknown_terms():
    docs = [tokenize(t) for t in ["rầy xanh hại chè", "bệnh thối búp trên chè", "kỹ thuật đốn chè"]]
    index = BM25Index(docs)
    scores = index.score(tokenize("thối búp"))
    assert scores.argmax() == 1
    assert index.score(["không_có_trong_từ_điển"]).sum() == 0


def test_bm25_empty_corpus():
    assert BM25Index([]).score(["a"]).shape == (0,)


def test_min_max_scaling():
    assert min_max({"a": 2.0, "b": 4.0}) == {"a": 0.5, "b": 1.0}
    assert min_max({"a": 0.0}) == {"a": 0.0}
    assert min_max({}) == {}


def test_metrics():
    ranked = ["x", "a", "y"]
    relevant = {"a", "b"}
    assert hit_at_k(ranked, relevant, 1) == 0.0
    assert hit_at_k(ranked, relevant, 2) == 1.0
    assert reciprocal_rank(ranked, relevant) == 0.5
    assert precision_at_k(ranked, relevant, 3) == pytest.approx(1 / 3)
    assert 0 < ndcg_at_k(ranked, relevant, 3) < 1
    assert ndcg_at_k(["a", "b"], relevant, 2) == pytest.approx(1.0)
    assert reciprocal_rank(["x"], relevant) == 0.0


def test_summarize_ranking():
    summary = summarize_ranking([{"ranked_ids": ["a"], "relevant": {"a"}}, {"ranked_ids": ["x"], "relevant": {"a"}}])
    assert summary["hit@1"] == 0.5 and summary["mrr"] == 0.5


def test_robustness_typo_generator_is_deterministic():
    from rag.evaluation.robustness import swap_typos
    assert swap_typos("bệnh thối búp trên cây chè") == swap_typos("bệnh thối búp trên cây chè")


def test_chunk_to_record_builds_embedding_text_and_scalar_metadata():
    item = {
        "chunk_id": "tea_000001", "title": "Tiêu đề", "content": "Nội dung", "source": "TL1",
        "source_type": "technical_document", "category": "cultivation_technique",
        "metadata": {"page": None, "year": 2020},
    }
    chunk_id, content, meta, embed_text = chunk_to_record(item)
    assert chunk_id == "tea_000001" and content == "Nội dung"
    assert embed_text == build_index_text("Tiêu đề", "Nội dung") and "Tiêu đề" in embed_text
    assert meta["page"] == -1 and meta["year"] == 2020  # ChromaDB không nhận None
    assert all(isinstance(v, (str, int, float, bool)) for v in meta.values())


def test_eval_set_is_well_formed():
    queries = load_eval_set()
    ids = [q["id"] for q in queries]
    assert len(ids) == len(set(ids))
    for q in queries:
        assert q["type"] in {"in_domain", "out_of_domain", "knowledge_gap"}
        if q["type"] == "in_domain":
            assert q["relevant_chunk_ids"], q["id"]
        else:
            assert not q["relevant_chunk_ids"], q["id"]


# ---------------------------------------------------------------- index (chỉ mục thật)
@pytest.fixture(scope="module")
def retriever():
    r = RAGRetriever()
    r.load()
    return r


def test_retrieve_returns_structured_result(retriever):
    res = retriever.retrieve("Bệnh thối búp trên cây chè có triệu chứng gì?", top_k=3)
    assert res["is_relevant"] is True
    assert res["count"] == 3
    assert res["retrieved_chunks"][0]["chunk_id"] == "tea_000032"
    first = res["retrieved_chunks"][0]
    assert {"similarity_score", "bm25_score", "hybrid_score", "metadata", "content"} <= first.keys()
    assert 0.0 <= first["similarity_score"] <= 1.0
    assert "tea_000032" in res["context_text"]
    assert res["sources"][0]["chunk_id"] == "tea_000032"


def test_unaccented_query_finds_the_right_chunk_and_passes_the_gate(retriever):
    res = retriever.retrieve("benh thoi bup tren cay che co trieu chung gi", top_k=3)
    assert res["unaccented"] is True
    assert res["is_relevant"] is True
    assert "tea_000032" in [c["chunk_id"] for c in res["retrieved_chunks"]]


def test_unaccented_out_of_domain_is_rejected(retriever):
    assert retriever.retrieve("gia bitcoin hom nay la bao nhieu", top_k=3)["is_relevant"] is False


def test_retrieve_rejects_out_of_domain(retriever):
    res = retriever.retrieve("Giá Bitcoin hôm nay là bao nhiêu?")
    assert res["is_relevant"] is False


def test_retrieve_handles_empty_query(retriever):
    res = retriever.retrieve("   ")
    assert res["retrieved_chunks"] == [] and res["is_relevant"] is False


def test_retrieve_metadata_filter(retriever):
    res = retriever.retrieve("triệu chứng bệnh", top_k=5, disease="bệnh thối búp")
    assert res["retrieved_chunks"]
    assert all(c["metadata"]["disease"] == "bệnh thối búp" for c in res["retrieved_chunks"])
    assert retriever.retrieve("triệu chứng", disease="không tồn tại")["retrieved_chunks"] == []


def test_retrieve_modes_return_ranked_results(retriever):
    for mode in (MODE_DENSE, MODE_BM25, MODE_HYBRID):
        res = retriever.retrieve("nhện đỏ hại chè", top_k=3, mode=mode)
        scores = [c["hybrid_score"] for c in res["retrieved_chunks"]]
        assert scores == sorted(scores, reverse=True)


def test_ranking_quality_regression(retriever):
    """Số đo thực tế (bkai + BM25): Hit@1=0.92, Hit@3=0.99, MRR=0.95. Ngưỡng ở đây thấp hơn để chỉ báo khi tụt rõ rệt."""
    metrics = evaluate_ranking(retriever, load_eval_set(), MODE_HYBRID)
    assert metrics["hit@3"] >= 0.93
    assert metrics["hit@1"] >= 0.85
    assert metrics["mrr"] >= 0.90


def test_hybrid_beats_dense_baseline(retriever):
    queries = load_eval_set()
    dense = evaluate_ranking(retriever, queries, MODE_DENSE)
    hybrid = evaluate_ranking(retriever, queries, MODE_HYBRID)
    assert hybrid["mrr"] > dense["mrr"]


def test_gate_accepts_all_in_domain_and_rejects_most_out_of_scope(retriever):
    gate = evaluate_gate(retriever, load_eval_set())
    assert gate["accept_in_domain"] >= 0.95
    assert gate["reject_out_of_scope"] >= 0.9  # số đo thực tế 1.0 với bkai; model MiniLM cũ chỉ đạt 0.58
