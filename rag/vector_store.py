from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np

from rag.config import COLLECTION_NAME, FOLDED_COLLECTION_NAME, INDEX_VERSION, MODEL_NAME, VECTOR_STORE_DIR
from rag.embeddings import EmbeddingEngine


class IndexNotReadyError(RuntimeError):
    """Chỉ mục vector chưa được tạo hoặc đã cũ so với mã nguồn."""


@dataclass
class IndexSnapshot:
    ids: List[str]
    documents: List[str]
    metadatas: List[Dict[str, Any]]
    embeddings: np.ndarray  # (n, dim), đã chuẩn hóa L2
    embeddings_folded: np.ndarray  # embedding của văn bản đã bỏ dấu, cùng thứ tự với `ids`


class VectorStoreManager:
    """
    Lưu trữ bền vững các chunk và embedding bằng ChromaDB.

    ChromaDB đóng vai trò kho lưu trữ; việc xếp hạng hybrid (vector + BM25) cần điểm của toàn bộ
    chunk nên retriever nạp snapshot vào bộ nhớ một lần (kho hiện có vài trăm chunk, ~vài trăm KB).
    """

    def __init__(self, persist_dir: str = str(VECTOR_STORE_DIR), collection_name: str = COLLECTION_NAME):
        import chromadb

        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.embedding_engine: Optional[EmbeddingEngine] = None
        self.client = chromadb.PersistentClient(path=persist_dir)

    # ------------------------------------------------------------------ ghi
    def rebuild(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        embed_texts: List[str],
        folded_embed_texts: List[str],
    ) -> int:
        """
        Xóa collection cũ và lập chỉ mục lại từ đầu (tránh chunk mồ côi khi kho tri thức thay đổi).
        `documents` là nội dung lưu trữ; `embed_texts` là văn bản dùng để tạo embedding.
        """
        if not (len(ids) == len(documents) == len(metadatas) == len(embed_texts) == len(folded_embed_texts)):
            raise ValueError("ids, documents, metadatas, embed_texts và folded_embed_texts phải cùng độ dài")
        if len(set(ids)) != len(ids):
            raise ValueError("chunk_id bị trùng lặp")

        for name in (self.collection_name, FOLDED_COLLECTION_NAME):
            try:
                self.client.delete_collection(name)
            except Exception:
                pass  # collection chưa tồn tại

        collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine", "index_version": INDEX_VERSION, "model": MODEL_NAME},
        )
        embeddings = self._engine().encode(embed_texts)
        collection.add(ids=ids, embeddings=embeddings.tolist(), documents=documents, metadatas=metadatas)

        folded = self.client.create_collection(
            name=FOLDED_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine", "index_version": INDEX_VERSION, "model": MODEL_NAME},
        )
        folded.add(ids=ids, embeddings=self._engine().encode(folded_embed_texts).tolist())
        return collection.count()

    # ------------------------------------------------------------------ đọc
    def load_snapshot(self) -> IndexSnapshot:
        """Đọc toàn bộ chỉ mục; báo lỗi rõ ràng nếu chưa ingest hoặc chỉ mục cũ."""
        try:
            collection = self.client.get_collection(self.collection_name)
        except Exception as err:
            raise IndexNotReadyError(
                f"Chưa có chỉ mục vector '{self.collection_name}'. Chạy: python -m rag.ingest"
            ) from err

        version = (collection.metadata or {}).get("index_version")
        if version != INDEX_VERSION:
            raise IndexNotReadyError(
                f"Chỉ mục vector đã cũ (phiên bản {version!r}, cần {INDEX_VERSION!r}). Chạy: python -m rag.ingest"
            )

        data = collection.get(include=["documents", "metadatas", "embeddings"])
        if not data["ids"]:
            raise IndexNotReadyError("Chỉ mục vector rỗng. Chạy: python -m rag.ingest")

        try:
            folded_data = self.client.get_collection(FOLDED_COLLECTION_NAME).get(include=["embeddings"])
        except Exception as err:
            raise IndexNotReadyError(
                "Thiếu chỉ mục vector bỏ dấu (câu hỏi không dấu sẽ không hoạt động). Chạy: python -m rag.ingest"
            ) from err
        folded_by_id = {cid: emb for cid, emb in zip(folded_data["ids"], folded_data["embeddings"])}
        if set(folded_by_id) != set(data["ids"]):
            raise IndexNotReadyError("Chỉ mục bỏ dấu không khớp chỉ mục chính. Chạy: python -m rag.ingest")

        return IndexSnapshot(
            ids=list(data["ids"]),
            documents=list(data["documents"]),
            metadatas=list(data["metadatas"]),
            embeddings=np.asarray(data["embeddings"], dtype=float),
            embeddings_folded=np.asarray([folded_by_id[cid] for cid in data["ids"]], dtype=float),
        )

    def encode_query(self, text: str) -> np.ndarray:
        return self._engine().encode([text])[0]

    def count(self) -> int:
        try:
            return self.client.get_collection(self.collection_name).count()
        except Exception:
            return 0

    def _engine(self) -> EmbeddingEngine:
        if self.embedding_engine is None:
            self.embedding_engine = EmbeddingEngine()
        return self.embedding_engine
