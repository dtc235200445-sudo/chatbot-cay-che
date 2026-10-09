import numpy as np
from typing import List, Union

from rag import config


class EmbeddingEngine:
    """
    Embedding tiếng Việt (mặc định `bkai-foundation-models/vietnamese-bi-encoder`, 768 chiều).
    Vector được chuẩn hóa L2 nên tích vô hướng chính là cosine similarity.

    Với model dựa trên PhoBERT, văn bản được tách từ bằng pyvi trước khi mã hóa (bắt buộc để model hoạt động đúng);
    việc này áp dụng giống nhau cho đoạn tài liệu và câu hỏi.
    """

    def __init__(
        self,
        model_name: str = config.MODEL_NAME,
        segment_words: bool = config.SEGMENT_WORDS,
        max_seq_length: int = config.MAX_SEQ_LENGTH,
    ):
        self.model_name = model_name
        self.segment_words = segment_words
        self._segment = None
        if segment_words:
            try:
                from pyvi import ViTokenizer
            except ImportError as e:
                raise RuntimeError("Model embedding tiếng Việt cần thư viện pyvi: pip install pyvi") from e
            self._segment = ViTokenizer.tokenize
        try:
            from sentence_transformers import SentenceTransformer
            self.st_model = SentenceTransformer(model_name)
            self.st_model.max_seq_length = max_seq_length
        except Exception as e:
            raise RuntimeError(f"[RAG Embeddings] Failed to load SentenceTransformer model '{model_name}': {e}")

    def encode(self, texts: Union[str, List[str]]) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]
        if self._segment is not None:
            texts = [self._segment(t) for t in texts]
        return self.st_model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
