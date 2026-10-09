# Đánh giá mở rộng tầng truy xuất (khắc phục các hạn chế của lượt so sánh đầu)

Không gọi LLM. Cùng 171 chunk, cùng 928 câu trong phạm vi RAG (trừ khi nêu khác). Khoảng trong ngoặc vuông là khoảng tin cậy Wilson 95%.

## 1. Nhãn đúng chỉ là một chunk: nhãn chặt và nhãn nới lỏng

Nhãn chặt: top-k phải chứa đúng `source_chunk_id`. Nhãn nới lỏng: các chunk trong top-k **phủ ít nhất 50%** các cụm 4 từ của đoạn nguồn, không phụ thuộc chunk nào chứa nội dung đó.

Mức nhập nhằng của nhãn: **77/928 câu** có một chunk KHÁC cũng phủ ≥50% đoạn nguồn.

| Hệ thống | Hit@3 chặt | Hit@3 nới lỏng | Hit@1 chặt | Hit@1 nới lỏng |
|---|---|---|---|---|
| all-MiniLM-L6-v2 | 0.235 [0.21-0.26] | 0.235 [0.21-0.26] | 0.135 [0.11-0.16] | 0.136 [0.12-0.16] |
| paraphrase-multilingual-MiniLM | 0.301 [0.27-0.33] | 0.305 [0.28-0.34] | 0.177 [0.15-0.20] | 0.180 [0.16-0.21] |
| bkai dense | 0.878 [0.86-0.90] | 0.883 [0.86-0.90] | 0.702 [0.67-0.73] | 0.716 [0.69-0.74] |
| BM25 tiếng Việt | 0.982 [0.97-0.99] | 0.982 [0.97-0.99] | 0.926 [0.91-0.94] | 0.926 [0.91-0.94] |
| Tea AI hybrid | 0.991 [0.98-1.00] | 0.991 [0.98-1.00] | 0.929 [0.91-0.94] | 0.929 [0.91-0.94] |

## 2. Câu hỏi không sinh từ chính chunk

### 2a. Bộ viết tay (`eval_set.json`, 72 câu trong phạm vi, nhãn do người gán)

Lưu ý: siêu tham số của Tea AI (alpha, ngưỡng cổng) được hiệu chỉnh trên chính bộ này nên số của Tea AI có thể lạc quan; các hệ thống RAG thường không bị ảnh hưởng.

| Hệ thống | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| all-MiniLM-L6-v2 | 0.333 | 0.472 | 0.514 | 0.405 |
| paraphrase-multilingual-MiniLM | 0.514 | 0.708 | 0.750 | 0.609 |
| bkai dense | 0.847 | 0.931 | 0.958 | 0.891 |
| BM25 tiếng Việt | 0.889 | 0.986 | 0.986 | 0.933 |
| Tea AI hybrid | 0.917 | 0.986 | 1.000 | 0.950 |

### 2b. Bộ câu hỏi lệch từ vựng (LLM viết lại bằng lời đời thường, không chép thuật ngữ của chunk)

Model sinh `openai/gpt-oss-20b`; 182 câu sinh ra từ 91 chunk. Độ trùng từ nội dung giữa câu hỏi và chunk nguồn: bộ 928 câu gốc trung bình **0.32**, câu mới sinh chưa lọc **0.47** (LLM chưa tự tránh được từ ngữ tài liệu nên phải lọc thêm). Bộ lọc ≤ 0.5 ban đầu KHÔNG làm câu hỏi lệch hơn bộ gốc, vì vậy dùng hai tập con lọc chặt hơn:

**Tập trùng từ ≤ 0.35**: 60 câu từ 43 chunk, độ trùng từ trung bình 0.22.

| Hệ thống | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| all-MiniLM-L6-v2 | 0.050 [0.02-0.14] | 0.067 [0.03-0.16] | 0.100 [0.05-0.20] | 0.066 |
| paraphrase-multilingual-MiniLM | 0.100 [0.05-0.20] | 0.250 [0.16-0.37] | 0.317 [0.21-0.44] | 0.185 |
| bkai dense | 0.167 [0.09-0.28] | 0.367 [0.26-0.49] | 0.433 [0.32-0.56] | 0.269 |
| BM25 tiếng Việt | 0.133 [0.07-0.24] | 0.317 [0.21-0.44] | 0.383 [0.27-0.51] | 0.227 |
| Tea AI hybrid | 0.217 [0.13-0.34] | 0.333 [0.23-0.46] | 0.450 [0.33-0.58] | 0.291 |

**Tập trùng từ ≤ 0.20 (rất lệch)**: 24 câu từ 18 chunk, độ trùng từ trung bình 0.10.

| Hệ thống | Hit@1 | Hit@3 | Hit@5 | MRR |
|---|---|---|---|---|
| all-MiniLM-L6-v2 | 0.000 [0.00-0.14] | 0.000 [0.00-0.14] | 0.000 [0.00-0.14] | 0.000 |
| paraphrase-multilingual-MiniLM | 0.167 [0.07-0.36] | 0.250 [0.12-0.45] | 0.292 [0.15-0.49] | 0.217 |
| bkai dense | 0.083 [0.02-0.26] | 0.333 [0.18-0.53] | 0.417 [0.24-0.61] | 0.201 |
| BM25 tiếng Việt | 0.000 [0.00-0.14] | 0.083 [0.02-0.26] | 0.083 [0.02-0.26] | 0.035 |
| Tea AI hybrid | 0.083 [0.02-0.26] | 0.125 [0.04-0.31] | 0.250 [0.12-0.45] | 0.131 |


## 3. Độ bền khi người dùng gõ nhầm (Hit@3 chặt, 928 câu)

| Hệ thống | gõ nhầm (có dấu) | gõ nhầm + không dấu |
|---|---|---|
| all-MiniLM-L6-v2 | 0.149 [0.13-0.17] | 0.161 [0.14-0.19] |
| paraphrase-multilingual-MiniLM | 0.178 [0.15-0.20] | 0.034 [0.02-0.05] |
| bkai dense | 0.652 [0.62-0.68] | 0.371 [0.34-0.40] |
| BM25 tiếng Việt | 0.883 [0.86-0.90] | 0.873 [0.85-0.89] |
| Tea AI hybrid | 0.920 [0.90-0.94] | 0.864 [0.84-0.88] |

## 4. Độ trễ truy xuất (ms/câu, chạy trên CPU, không có LLM; 100 câu, bỏ 3 lượt khởi động)

| Hệ thống | Trung vị | P95 |
|---|---|---|
| all-MiniLM-L6-v2 | 13.2 | 19.8 |
| paraphrase-multilingual-MiniLM | 21.9 | 28.0 |
| bkai dense | 53.6 | 68.3 |
| BM25 tiếng Việt | 57.3 | 68.6 |
| Tea AI hybrid | 57.6 | 67.7 |

## 5. Ảnh hưởng của chiến lược chunking (nhãn nới lỏng, Hit@3, 928 câu)

Chia lại cùng văn bản bằng cửa sổ cố định theo số từ; tiêu đề chunk = tên tài liệu (mất tiêu đề theo mục). "Từ ngữ cảnh" = số từ trung bình của top-3 chunk đưa cho LLM (chi phí prompt).

| Cách chia | Số chunk | Hệ thống | Hit@3 nới lỏng | Từ ngữ cảnh TB |
|---|---|---|---|---|
| gốc (theo mục, ~95 từ/chunk) | 171 | paraphrase-multilingual-MiniLM | 0.305 [0.28-0.34] | 353 |
| gốc (theo mục, ~95 từ/chunk) | 171 | Tea AI hybrid | 0.991 [0.98-1.00] | 302 |
| cố định 50 từ (chồng 10) | 407 | paraphrase-multilingual-MiniLM | 0.150 [0.13-0.17] | 150 |
| cố định 50 từ (chồng 10) | 407 | Tea AI hybrid | 0.423 [0.39-0.46] | 149 |
| cố định 100 từ (chồng 20) | 205 | paraphrase-multilingual-MiniLM | 0.242 [0.22-0.27] | 291 |
| cố định 100 từ (chồng 20) | 205 | Tea AI hybrid | 0.608 [0.58-0.64] | 293 |
| cố định 200 từ (chồng 40) | 103 | paraphrase-multilingual-MiniLM | 0.255 [0.23-0.28] | 563 |
| cố định 200 từ (chồng 40) | 103 | Tea AI hybrid | 0.669 [0.64-0.70] | 576 |
