# Kết quả đánh giá RAG

Bộ câu hỏi: 72 câu trong phạm vi + 12 câu ngoài phạm vi/thiếu tri thức. Cấu hình: alpha=0.7, MIN_COSINE=0.38, MIN_BM25=10.0.

## Chất lượng xếp hạng (câu hỏi trong phạm vi)

| Phương pháp | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 | P@3 |
|---|---|---|---|---|---|---|
| dense | 0.847 | 0.931 | 0.958 | 0.891 | 0.782 | 0.519 |
| bm25 | 0.889 | 0.986 | 0.986 | 0.933 | 0.823 | 0.556 |
| hybrid | 0.917 | 0.986 | 1.000 | 0.950 | 0.863 | 0.593 |

## Cổng từ chối câu hỏi ngoài cơ sở tri thức

- Nhận đúng câu trong phạm vi: 100.0%
- Từ chối đúng câu ngoài phạm vi/thiếu tri thức: 100.0%
