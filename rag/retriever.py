from typing import Any, Dict, List, Optional

import numpy as np

from rag import config
from rag.bm25 import BM25Index
from rag.context_builder import ContextBuilder
from rag.text_utils import build_bm25_text, is_unaccented, tokenize
from rag.vector_store import IndexSnapshot, VectorStoreManager

MODE_HYBRID = "hybrid"
MODE_DENSE = "dense"
MODE_BM25 = "bm25"


class RAGRetriever:
    """
    Truy xuất hybrid: cosine (embedding đa ngữ) kết hợp BM25 (khớp từ khóa/thuật ngữ chuyên môn).

    Kết quả trả về có `is_relevant` để tầng trên quyết định từ chối khi câu hỏi nằm ngoài cơ sở tri thức.
    """

    def __init__(self, vector_store: Optional[VectorStoreManager] = None):
        self.vector_store = vector_store or VectorStoreManager()
        self.context_builder = ContextBuilder()
        self._snapshot: Optional[IndexSnapshot] = None
        self._bm25: Optional[BM25Index] = None

    # ------------------------------------------------------------------ khởi tạo
    def load(self) -> None:
        snapshot = self.vector_store.load_snapshot()
        docs = [
            tokenize(build_bm25_text(meta.get("title", ""), doc, config.BM25_TITLE_BOOST))
            for doc, meta in zip(snapshot.documents, snapshot.metadatas)
        ]
        self._bm25 = BM25Index(docs, k1=config.BM25_K1, b=config.BM25_B)
        self._snapshot = snapshot
        # Nạp sẵn model embedding (mất vài chục giây lần đầu) để câu hỏi đầu tiên của người dùng không phải chờ.
        self.vector_store.encode_query("khởi động")

    def _ensure_loaded(self) -> IndexSnapshot:
        if self._snapshot is None:
            self.load()
        return self._snapshot

    # ------------------------------------------------------------------ truy xuất
    def retrieve(
        self,
        query: str,
        top_k: int = config.DEFAULT_TOP_K,
        category: Optional[str] = None,
        disease: Optional[str] = None,
        source: Optional[str] = None,
        mode: str = MODE_HYBRID,
    ) -> Dict[str, Any]:
        clean_query = query.strip()
        if not clean_query:
            return self._empty_result(query, "Câu hỏi không hợp lệ.")

        snapshot = self._ensure_loaded()

        # Câu gõ không dấu so với chỉ mục vector bỏ dấu (so với chỉ mục có dấu thì cosine sụp: Hit@3 vector 0,39 so với 0,82)
        unaccented = is_unaccented(clean_query)
        doc_vectors = snapshot.embeddings_folded if unaccented else snapshot.embeddings
        cosine = doc_vectors @ self.vector_store.encode_query(clean_query)
        bm25 = self._bm25.score(tokenize(clean_query))

        allowed = self._filter_indices(snapshot, category, disease, source)
        if not allowed:
            return self._empty_result(clean_query, "Không tìm thấy tri thức liên quan trong Kho dữ liệu Cây chè.")

        idx = np.array(allowed)
        cos_sub, bm_sub = cosine[idx], bm25[idx]
        top_cosine = float(cos_sub.max())
        top_bm25 = float(bm_sub.max())

        bm_norm = bm_sub / top_bm25 if top_bm25 > 0 else np.zeros_like(bm_sub)
        if mode == MODE_DENSE:
            ranking_score = cos_sub
        elif mode == MODE_BM25:
            ranking_score = bm_norm
        else:
            ranking_score = config.HYBRID_ALPHA * cos_sub + (1 - config.HYBRID_ALPHA) * bm_norm

        order = np.argsort(-ranking_score)[:top_k]
        retrieved: List[Dict[str, Any]] = []
        for pos in order:
            i = int(idx[pos])
            retrieved.append({
                "chunk_id": snapshot.ids[i],
                "content": snapshot.documents[i],
                "metadata": snapshot.metadatas[i],
                "similarity_score": round(float(max(0.0, min(1.0, cosine[i]))), 4),
                "bm25_score": round(float(bm25[i]), 3),
                "hybrid_score": round(float(ranking_score[pos]), 4),
            })

        strong = config.UNACCENTED_STRONG_COSINE if unaccented else config.STRONG_COSINE
        minimum = config.UNACCENTED_MIN_COSINE if unaccented else config.MIN_COSINE
        is_relevant = top_cosine >= strong or (top_cosine >= minimum and top_bm25 >= config.MIN_BM25)
        return {
            "query": clean_query,
            "context_text": self.context_builder.build_context(retrieved),
            "retrieved_chunks": retrieved,
            "sources": self.context_builder.extract_sources(retrieved),
            "count": len(retrieved),
            "top_cosine": round(top_cosine, 4),
            "top_bm25": round(top_bm25, 3),
            "is_relevant": is_relevant,
            "unaccented": unaccented,
        }

    # ------------------------------------------------------------------ nội bộ
    @staticmethod
    def _filter_indices(
        snapshot: IndexSnapshot, category: Optional[str], disease: Optional[str], source: Optional[str]
    ) -> List[int]:
        allowed = []
        for i, meta in enumerate(snapshot.metadatas):
            if category and meta.get("category") != category:
                continue
            if disease and meta.get("disease") != disease:
                continue
            if source and source.lower() not in (meta.get("source") or "").lower():
                continue
            allowed.append(i)
        return allowed

    @staticmethod
    def _empty_result(query: str, message: str) -> Dict[str, Any]:
        return {
            "query": query,
            "context_text": message,
            "retrieved_chunks": [],
            "sources": [],
            "count": 0,
            "top_cosine": 0.0,
            "top_bm25": 0.0,
            "is_relevant": False,
        }
