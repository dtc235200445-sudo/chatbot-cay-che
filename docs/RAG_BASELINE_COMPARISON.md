# So sánh Tea AI với RAG thường (tầng truy xuất)

Bộ câu hỏi: `E:\NHÁP 2\tea_chatbot_qa_test_1000.jsonl` — **928 câu thuộc phạm vi RAG** (đã loại 72 câu `Tea_Regions_Project_Config`, nguồn này không nằm trong kho vector). Cùng 171 chunk của `data/knowledge_base.json`, top-5, không gọi LLM. Nhãn đúng = `source_chunk_id`.

**Các hệ thống** (xếp từ RAG thường nhất đến Tea AI đầy đủ; mỗi bước thêm một thành phần):

- V1 RAG thường (all-MiniLM-L6-v2, dense)
- V2 RAG thường đa ngữ (paraphrase-multilingual-MiniLM, dense)
- T1 + embedding tiếng Việt (bkai, dense)
- T2 BM25 tiếng Việt (từ đơn + bigram, bỏ dấu)
- T3 Tea AI hybrid đầy đủ (bkai + BM25 + chỉ mục bỏ dấu)

RAG thường (V1, V2): embed nội dung chunk nguyên trạng bằng model có sẵn, cosine, lấy top-k, không có BM25, không ghép tiêu đề, không tách từ tiếng Việt, không chỉ mục bỏ dấu, không cổng từ chối.


## 1. Tổng thể (928 câu, gõ có dấu)

| Hệ thống | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 |
|---|---|---|---|---|---|
| V1 RAG thường (all-MiniLM-L6-v2, dense) | 0.135 | 0.235 | 0.292 | 0.191 | 0.192 |
| V2 RAG thường đa ngữ (paraphrase-multilingual-MiniLM, dense) | 0.177 | 0.301 | 0.387 | 0.250 | 0.248 |
| T1 + embedding tiếng Việt (bkai, dense) | 0.702 | 0.878 | 0.921 | 0.789 | 0.805 |
| T2 BM25 tiếng Việt (từ đơn + bigram, bỏ dấu) | 0.926 | 0.982 | 0.996 | 0.954 | 0.959 |
| T3 Tea AI hybrid đầy đủ (bkai + BM25 + chỉ mục bỏ dấu) | 0.929 | 0.991 | 1.000 | 0.957 | 0.964 |

## 2. Câu hỏi gõ không dấu (cùng câu, bỏ dấu tiếng Việt)

Người dùng thật thường gõ không dấu; RAG thường không có xử lý riêng cho trường hợp này.

| Hệ thống | Hit@1 | Hit@3 | Hit@5 | MRR | nDCG@3 |
|---|---|---|---|---|---|
| V1 RAG thường (all-MiniLM-L6-v2, dense) | 0.153 | 0.246 | 0.301 | 0.207 | 0.207 |
| V2 RAG thường đa ngữ (paraphrase-multilingual-MiniLM, dense) | 0.017 | 0.046 | 0.072 | 0.035 | 0.033 |
| T1 + embedding tiếng Việt (bkai, dense) | 0.505 | 0.673 | 0.740 | 0.598 | 0.606 |
| T2 BM25 tiếng Việt (từ đơn + bigram, bỏ dấu) | 0.922 | 0.978 | 0.995 | 0.952 | 0.956 |
| T3 Tea AI hybrid đầy đủ (bkai + BM25 + chỉ mục bỏ dấu) | 0.906 | 0.973 | 0.986 | 0.941 | 0.947 |

## 3. Theo loại câu hỏi (Hit@3 / MRR)

| Hệ thống | completeness | direct_grounded | domain_question | numeric_extraction | paraphrase | source_constrained |
|---|---|---|---|---|---|---|
| V1 RAG thường (all-MiniLM-L6-v2, dense) | 0.146 / 0.123 | 0.275 / 0.226 | 0.263 / 0.214 | 0.247 / 0.175 | 0.257 / 0.209 | 0.228 / 0.189 |
| V2 RAG thường đa ngữ (paraphrase-multilingual-MiniLM, dense) | 0.257 / 0.213 | 0.368 / 0.306 | 0.251 / 0.211 | 0.370 / 0.298 | 0.327 / 0.271 | 0.269 / 0.226 |
| T1 + embedding tiếng Việt (bkai, dense) | 0.901 / 0.804 | 0.953 / 0.891 | 0.912 / 0.830 | 0.849 / 0.803 | 0.877 / 0.800 | 0.760 / 0.617 |
| T2 BM25 tiếng Việt (từ đơn + bigram, bỏ dấu) | 0.994 / 0.980 | 0.994 / 0.990 | 0.988 / 0.977 | 1.000 / 0.991 | 0.988 / 0.977 | 0.936 / 0.831 |
| T3 Tea AI hybrid đầy đủ (bkai + BM25 + chỉ mục bỏ dấu) | 0.994 / 0.983 | 1.000 / 0.996 | 1.000 / 0.985 | 1.000 / 0.993 | 1.000 / 0.993 | 0.959 / 0.810 |

## 4. Theo nguồn tài liệu (Hit@3 / MRR)

| Hệ thống | FAO_EcoCrop_Camellia_sinensis (n=36) | LaiChau_Tea_Technical_Guideline (n=255) | TL1_Tea_Technical_Guideline (n=505) | Tang2020_Tea_Nutrient_QUEFTS (n=18) | TeaLeafDiseaseBD (n=114) |
|---|---|---|---|---|---|
| V1 RAG thường (all-MiniLM-L6-v2, dense) | 0.750 / 0.544 | 0.243 / 0.198 | 0.119 / 0.091 | 0.611 / 0.532 | 0.509 / 0.453 |
| V2 RAG thường đa ngữ (paraphrase-multilingual-MiniLM, dense) | 0.861 / 0.785 | 0.251 / 0.191 | 0.188 / 0.148 | 0.667 / 0.528 | 0.675 / 0.616 |
| T1 + embedding tiếng Việt (bkai, dense) | 1.000 / 0.981 | 0.851 / 0.752 | 0.857 / 0.757 | 1.000 / 1.000 | 0.974 / 0.923 |
| T2 BM25 tiếng Việt (từ đơn + bigram, bỏ dấu) | 1.000 / 1.000 | 0.969 / 0.915 | 0.982 / 0.959 | 1.000 / 1.000 | 1.000 / 1.000 |
| T3 Tea AI hybrid đầy đủ (bkai + BM25 + chỉ mục bỏ dấu) | 1.000 / 1.000 | 0.980 / 0.903 | 0.994 / 0.969 | 1.000 / 1.000 | 1.000 / 1.000 |

## 5. Cổng từ chối câu hỏi ngoài cơ sở tri thức

Bộ `rag/evaluation/eval_set.json`: 72 câu trong phạm vi, 12 câu ngoài phạm vi/thiếu tri thức.

| Hệ thống | Nhận đúng câu trong phạm vi | Từ chối đúng câu ngoài phạm vi |
|---|---|---|
| V1 RAG thường (all-MiniLM-L6-v2, dense) | 100.0% (không có cổng, luôn trả top-k) | 0.0% |
| V2 RAG thường đa ngữ (paraphrase-multilingual-MiniLM, dense) | 100.0% (không có cổng, luôn trả top-k) | 0.0% |
| Tea AI (cổng cosine + BM25, cấu hình hiện tại) | 100.0% | 100.0% |

## 6. Ý nghĩa thống kê: Tea AI đầy đủ (T3) so với từng hệ thống, Hit@3

Bootstrap ghép cặp 2000 lần, kiểm định McNemar chính xác (hai phía).

| So với | Loại câu | Chênh Hit@3 (T3 − hệ thống đó) | KTC 95% | p (McNemar) |
|---|---|---|---|---|
| V1 RAG thường (all-MiniLM-L6-v2, dense) | có dấu | +0.756 | [+0.730, +0.784] | 9.5e-212 |
| V1 RAG thường (all-MiniLM-L6-v2, dense) | không dấu | +0.727 | [+0.698, +0.756] | 1.8e-199 |
| V2 RAG thường đa ngữ (paraphrase-multilingual-MiniLM, dense) | có dấu | +0.691 | [+0.659, +0.720] | 2.2e-193 |
| V2 RAG thường đa ngữ (paraphrase-multilingual-MiniLM, dense) | không dấu | +0.927 | [+0.909, +0.943] | 2.6e-259 |
| T1 + embedding tiếng Việt (bkai, dense) | có dấu | +0.113 | [+0.092, +0.134] | 1.8e-29 |
| T1 + embedding tiếng Việt (bkai, dense) | không dấu | +0.300 | [+0.269, +0.329] | 4.1e-84 |
| T2 BM25 tiếng Việt (từ đơn + bigram, bỏ dấu) | có dấu | +0.010 | [+0.001, +0.018] | 0.049 |
| T2 BM25 tiếng Việt (từ đơn + bigram, bỏ dấu) | không dấu | -0.005 | [-0.014, +0.004] | 0.36 |

## Lưu ý khi diễn giải

- Kho tri thức đã được chia chunk sẵn (171 chunk), nên so sánh này **không** đo ảnh hưởng của chiến lược chunking.
- Bộ câu hỏi được sinh từ chính các chunk nguồn, nhiều câu là paraphrase của cùng một chunk; nhãn đúng là đúng một chunk, nên số liệu có thể thấp hơn thực tế nếu nhiều chunk cùng chứa đáp án.
- Siêu tham số của Tea AI (alpha, ngưỡng cổng) được hiệu chỉnh trên `eval_set.json`, không phải trên bộ 1000 câu này.
- Đây là đánh giá tầng truy xuất. Chất lượng câu trả lời cuối cùng do LLM sinh ra được đo riêng (xem `QA1000_ANSWER_RESULTS.md`).
