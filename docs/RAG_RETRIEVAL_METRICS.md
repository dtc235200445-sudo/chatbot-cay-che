# Đánh giá tầng truy xuất: Context Precision, Context Recall, Precision@K, Recall@K, MRR

Không gọi LLM. 171 chunk. K = 3 (số chunk Tea AI đưa cho LLM) trừ khi ghi khác.

## Cách xác định chunk liên quan

Mỗi câu trong bộ 1000 câu có danh sách ý chính (`answer_key_points`) trích từ tài liệu. Một chunk được coi là **liên quan** nếu chứa ít nhất một ý chính (≥ 90% số cặp từ liền kề của ý chính xuất hiện trong chunk). Chunk nguồn luôn liên quan. Đánh giá trên **928 câu** (bỏ 72 câu thuộc nguồn vùng trồng, gồm cả 24 câu thiếu dữ liệu, vì nguồn này không có trong kho vector).

Số chunk liên quan mỗi câu: 1 chunk: 841 câu, 2 chunk: 59 câu, 3 chunk: 23 câu, ≥5 chunk: 5 câu.

| Chỉ số | Trả lời câu hỏi | Công thức |
|---|---|---|
| Context Precision@K | Chunk liên quan có nằm ở đầu danh sách không | Trung bình Precision@k tại các vị trí k có chunk liên quan |
| Context Recall@K | Top-K có đủ ý để trả lời không | Số ý chính được phủ / tổng số ý chính |
| Precision@K | Trong K chunk lấy ra, bao nhiêu chunk liên quan | Số chunk liên quan trong top-K / K |
| Recall@K | Lấy được bao nhiêu phần trong các chunk liên quan | Số chunk liên quan trong top-K / tổng số chunk liên quan |
| MRR | Chunk liên quan đầu tiên đứng ở vị trí nào | Trung bình 1 / vị trí (0 nếu không có trong top-5) |

Precision@K bị giới hạn trên bởi (số chunk liên quan / K): phần lớn câu chỉ có 1 chunk liên quan nên Precision@3 tối đa khoảng 0.33. Chỉ số này dùng để so sánh giữa các hệ thống, không đọc như tỉ lệ tuyệt đối.


## Câu gốc (có dấu): 928 câu (nhãn từ ý chính)

| Hệ thống | Context Precision@3 | Context Recall@3 | Precision@3 | Recall@3 | MRR | Hit@3 |
|---|---|---|---|---|---|---|
| all-MiniLM-L6-v2 | 0.179 | 0.235 | 0.082 | 0.222 | 0.192 | 0.236 |
| paraphrase-multilingual-MiniLM | 0.233 | 0.301 | 0.109 | 0.291 | 0.252 | 0.305 |
| bkai dense | 0.781 | 0.878 | 0.314 | 0.856 | 0.793 | 0.878 |
| BM25 tiếng Việt | 0.949 | 0.982 | 0.349 | 0.958 | 0.954 | 0.982 |
| Tea AI hybrid | 0.953 | 0.991 | 0.357 | 0.972 | 0.957 | 0.991 |

Tea AI − RAG thường đa ngữ (khoảng tin cậy 95%, bootstrap 2000 lần): context precision +0.720 [+0.695, +0.746]; context recall +0.690 [+0.660, +0.719]; precision +0.248 [+0.236, +0.260]; recall +0.681 [+0.651, +0.710]; mrr +0.704 [+0.678, +0.728].


## Gõ không dấu: 928 câu (nhãn từ ý chính)

| Hệ thống | Context Precision@3 | Context Recall@3 | Precision@3 | Recall@3 | MRR | Hit@3 |
|---|---|---|---|---|---|---|
| all-MiniLM-L6-v2 | 0.195 | 0.246 | 0.087 | 0.232 | 0.208 | 0.248 |
| paraphrase-multilingual-MiniLM | 0.029 | 0.046 | 0.015 | 0.045 | 0.035 | 0.046 |
| bkai dense | 0.587 | 0.675 | 0.238 | 0.655 | 0.602 | 0.678 |
| BM25 tiếng Việt | 0.947 | 0.978 | 0.348 | 0.954 | 0.952 | 0.978 |
| Tea AI hybrid | 0.937 | 0.973 | 0.348 | 0.952 | 0.944 | 0.973 |

Tea AI − RAG thường đa ngữ (khoảng tin cậy 95%, bootstrap 2000 lần): context precision +0.908 [+0.893, +0.924]; context recall +0.927 [+0.911, +0.944]; precision +0.332 [+0.324, +0.341]; recall +0.907 [+0.889, +0.924]; mrr +0.909 [+0.894, +0.924].


## Gõ nhầm + không dấu: 928 câu (nhãn từ ý chính)

| Hệ thống | Context Precision@3 | Context Recall@3 | Precision@3 | Recall@3 | MRR | Hit@3 |
|---|---|---|---|---|---|---|
| all-MiniLM-L6-v2 | 0.117 | 0.161 | 0.054 | 0.152 | 0.130 | 0.161 |
| paraphrase-multilingual-MiniLM | 0.023 | 0.034 | 0.011 | 0.034 | 0.029 | 0.034 |
| bkai dense | 0.264 | 0.371 | 0.126 | 0.362 | 0.281 | 0.374 |
| BM25 tiếng Việt | 0.799 | 0.873 | 0.306 | 0.844 | 0.807 | 0.874 |
| Tea AI hybrid | 0.805 | 0.864 | 0.301 | 0.834 | 0.812 | 0.864 |

Tea AI − RAG thường đa ngữ (khoảng tin cậy 95%, bootstrap 2000 lần): context precision +0.782 [+0.759, +0.806]; context recall +0.830 [+0.804, +0.855]; precision +0.289 [+0.279, +0.300]; recall +0.799 [+0.774, +0.824]; mrr +0.783 [+0.759, +0.806].


## Viết tay (72 câu, người gán nhãn): 72 câu (nhãn người gán, nhiều chunk/câu)

| Hệ thống | Context Precision@3 | Context Recall@3 | Precision@3 | Recall@3 | MRR | Hit@3 |
|---|---|---|---|---|---|---|
| all-MiniLM-L6-v2 | 0.395 | 0.297 | 0.208 | 0.297 | 0.405 | 0.472 |
| paraphrase-multilingual-MiniLM | 0.586 | 0.467 | 0.338 | 0.467 | 0.609 | 0.708 |
| bkai dense | 0.878 | 0.706 | 0.519 | 0.706 | 0.891 | 0.931 |
| BM25 tiếng Việt | 0.920 | 0.750 | 0.556 | 0.750 | 0.933 | 0.986 |
| Tea AI hybrid | 0.943 | 0.773 | 0.593 | 0.773 | 0.950 | 0.986 |

Tea AI − RAG thường đa ngữ (khoảng tin cậy 95%, bootstrap 2000 lần): context precision +0.358 [+0.252, +0.465]; context recall +0.306 [+0.207, +0.404]; precision +0.255 [+0.171, +0.338]; recall +0.306 [+0.209, +0.408]; mrr +0.340 [+0.237, +0.447].


## Diễn đạt lại (60 câu): 60 câu (một chunk nguồn/câu, nhãn nhiễu)

| Hệ thống | Context Precision@3 | Context Recall@3 | Precision@3 | Recall@3 | MRR | Hit@3 |
|---|---|---|---|---|---|---|
| all-MiniLM-L6-v2 | 0.058 | 0.067 | 0.022 | 0.067 | 0.066 | 0.067 |
| paraphrase-multilingual-MiniLM | 0.169 | 0.250 | 0.083 | 0.250 | 0.185 | 0.250 |
| bkai dense | 0.253 | 0.367 | 0.122 | 0.367 | 0.269 | 0.367 |
| BM25 tiếng Việt | 0.211 | 0.317 | 0.106 | 0.317 | 0.227 | 0.317 |
| Tea AI hybrid | 0.264 | 0.333 | 0.111 | 0.333 | 0.291 | 0.333 |

Tea AI − RAG thường đa ngữ (khoảng tin cậy 95%, bootstrap 2000 lần): context precision +0.094 [-0.022, +0.206]; context recall +0.083 [-0.050, +0.217]; precision +0.028 [-0.017, +0.078]; recall +0.083 [-0.050, +0.217]; mrr +0.105 [-0.007, +0.213].


## Theo K (câu gốc có dấu)

| Hệ thống | CP@1 | CP@3 | CP@5 | CR@1 | CR@3 | CR@5 | P@1 | P@3 | P@5 | R@1 | R@3 | R@5 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| all-MiniLM-L6-v2 | 0.136 | 0.179 | 0.191 | 0.135 | 0.235 | 0.293 | 0.136 | 0.082 | 0.062 | 0.124 | 0.222 | 0.278 |
| paraphrase-multilingual-MiniLM | 0.178 | 0.233 | 0.253 | 0.177 | 0.301 | 0.388 | 0.178 | 0.109 | 0.084 | 0.165 | 0.291 | 0.376 |
| bkai dense | 0.707 | 0.781 | 0.789 | 0.703 | 0.878 | 0.922 | 0.707 | 0.314 | 0.201 | 0.665 | 0.856 | 0.905 |
| BM25 tiếng Việt | 0.926 | 0.949 | 0.946 | 0.926 | 0.982 | 0.996 | 0.926 | 0.349 | 0.219 | 0.878 | 0.958 | 0.983 |
| Tea AI hybrid | 0.929 | 0.953 | 0.953 | 0.929 | 0.991 | 1.000 | 0.929 | 0.357 | 0.219 | 0.882 | 0.972 | 0.985 |

CP = Context Precision, CR = Context Recall, P = Precision, R = Recall.


## Theo loại câu hỏi (câu gốc, Context Precision@3 / Context Recall@3)

| Hệ thống | completeness (n=171) | direct_grounded (n=171) | domain_question (n=171) | numeric_extraction (n=73) | paraphrase (n=171) | source_constrained (n=171) |
|---|---|---|---|---|---|---|
| all-MiniLM-L6-v2 | 0.11 / 0.15 | 0.21 / 0.27 | 0.20 / 0.26 | 0.15 / 0.25 | 0.20 / 0.26 | 0.17 / 0.23 |
| paraphrase-multilingual-MiniLM | 0.19 / 0.26 | 0.29 / 0.37 | 0.19 / 0.25 | 0.29 / 0.37 | 0.26 / 0.33 | 0.22 / 0.27 |
| bkai dense | 0.80 / 0.90 | 0.89 / 0.95 | 0.83 / 0.91 | 0.78 / 0.85 | 0.79 / 0.88 | 0.60 / 0.76 |
| BM25 tiếng Việt | 0.98 / 0.99 | 0.99 / 0.99 | 0.97 / 0.99 | 0.99 / 1.00 | 0.98 / 0.99 | 0.81 / 0.94 |
| Tea AI hybrid | 0.98 / 0.99 | 0.99 / 1.00 | 0.99 / 1.00 | 0.99 / 1.00 | 0.99 / 1.00 | 0.80 / 0.96 |

## Lưu ý khi diễn giải

- Liên quan được xác định bằng so khớp văn bản với ý chính, không phải LLM chấm như RAGAS gốc. Chunk diễn đạt cùng ý bằng từ ngữ khác sẽ không được tính là liên quan, nên Context Precision/Recall là cận dưới.
- Bộ viết tay và bộ diễn đạt lại không có ý chính; Context Recall ở hai bộ này bằng Recall@K theo nhãn chunk.
- Bộ diễn đạt lại chỉ có một chunk nguồn mỗi câu và còn nhãn nhiễu (xem RAG_EXTENDED_EVALUATION.md).
- Tea AI được hiệu chỉnh trên bộ viết tay nên số của Tea AI ở bộ này có thể lạc quan.
