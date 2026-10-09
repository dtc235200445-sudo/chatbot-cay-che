import math
from collections import Counter
from typing import Dict, List, Sequence, Tuple

import numpy as np


class BM25Index:
    """BM25 Okapi thuần Python/NumPy với chỉ mục ngược; đủ nhanh cho kho tri thức cỡ vài nghìn chunk."""

    def __init__(self, tokenized_docs: Sequence[Sequence[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.num_docs = len(tokenized_docs)
        self.doc_lengths = np.array([len(d) for d in tokenized_docs], dtype=float)
        self.avg_length = float(self.doc_lengths.mean()) if self.num_docs else 0.0

        postings: Dict[str, List[Tuple[int, int]]] = {}
        for doc_idx, tokens in enumerate(tokenized_docs):
            for term, freq in Counter(tokens).items():
                postings.setdefault(term, []).append((doc_idx, freq))

        self._postings = {
            term: (
                np.array([d for d, _ in plist], dtype=int),
                np.array([f for _, f in plist], dtype=float),
            )
            for term, plist in postings.items()
        }
        self._idf = {
            term: math.log(1 + (self.num_docs - len(plist) + 0.5) / (len(plist) + 0.5))
            for term, plist in postings.items()
        }

    def score(self, query_tokens: Sequence[str]) -> np.ndarray:
        """Điểm BM25 của mọi tài liệu đối với truy vấn (mảng độ dài num_docs)."""
        scores = np.zeros(self.num_docs)
        if not self.num_docs:
            return scores
        for term in set(query_tokens):
            entry = self._postings.get(term)
            if entry is None:
                continue
            doc_idx, freq = entry
            norm = self.k1 * (1 - self.b + self.b * self.doc_lengths[doc_idx] / self.avg_length)
            scores[doc_idx] += self._idf[term] * freq * (self.k1 + 1) / (freq + norm)
        return scores
