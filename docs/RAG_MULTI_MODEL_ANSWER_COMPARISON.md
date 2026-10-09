# So sánh Tea AI với RAG thường qua nhiều model sinh và model chấm

Mỗi dòng là một cấu hình (model sinh / model chấm). Model chấm luôn khác họ với model sinh. Tea AI = hybrid + cổng + prompt ràng buộc; RAG thường = embedding đa ngữ dense top-3 + prompt chung. Cùng câu hỏi cho hai hệ thống trong từng cấu hình.

## 1. Câu có đáp án chuẩn: điểm đầu-cuối (câu bị từ chối nhầm tính điểm thấp nhất)

| Model sinh / chấm | N cặp | Correctness Tea AI | Correctness RAG thường | Chênh lệch (KTC 95%) | Coverage Tea AI | Coverage RAG thường | Từ chối nhầm Tea AI | Từ chối nhầm RAG thường |
|---|---|---|---|---|---|---|---|---|
| gpt-oss-120b / qwen3.8-27b | 67 | 4.72 | 2.06 | +2.66 [+2.22, +3.04] | 0.946 | 0.269 | 1/67 | 25/67 |
| gpt-oss-20b / qwen3.8-27b | 24 | 4.58 | 2.25 | +2.33 [+1.67, +3.00] | 0.909 | 0.295 | 0/24 | 6/24 |
| qwen3.8-27b / gpt-oss-20b | 22 | 4.91 | 2.27 | +2.64 [+1.82, +3.36] | 0.994 | 0.306 | 1/24 | 1/24 |

## 2. Chỉ câu cả hai hệ thống đều được chấm (có điều kiện)

| Model sinh / chấm | N cặp | Correctness Tea AI / RAG thường | Faithfulness Tea AI / RAG thường | Coverage Tea AI / RAG thường | Chênh lệch correctness (KTC 95%) |
|---|---|---|---|---|---|
| gpt-oss-120b / qwen3.8-27b | 42 | 4.60 / 2.69 | 0.994 / 0.837 | 0.920 / 0.429 | +1.90 [+1.36, +2.45] |
| gpt-oss-20b / qwen3.8-27b | 18 | 4.78 / 2.67 | 1.000 / 0.687 | 0.925 / 0.393 | +2.11 [+1.28, +2.94] |
| qwen3.8-27b / gpt-oss-20b | 21 | 4.90 / 2.33 | 0.976 / 0.952 | 0.994 / 0.322 | +2.57 [+1.76, +3.29] |

## 3. Câu thiếu dữ liệu (phải từ chối, không bịa số liệu) và số liệu không căn cứ

| Model sinh / chấm | N câu thiếu dữ liệu | Từ chối đúng Tea AI / RAG thường | Bịa số liệu Tea AI / RAG thường | Câu có số liệu không căn cứ Tea AI / RAG thường |
|---|---|---|---|---|
| gpt-oss-120b / qwen3.8-27b | 24 | 24 / 24 | 0 / 0 | 0 / 9 |
| gpt-oss-20b / qwen3.8-27b | 8 | 8 / 8 | 0 / 0 | 1 / 8 |
| qwen3.8-27b / gpt-oss-20b | 8 | 8 / 8 | 0 / 0 | 0 / 2 |

## 4. Độ trễ trung bình một câu (s, gồm truy xuất và sinh; đo khi Groq còn giới hạn tốc độ nên chỉ mang tính tham khảo)

| Model sinh | Tea AI | RAG thường |
|---|---|---|
| gpt-oss-120b | 16.7 | 5.7 |
| gpt-oss-20b | 5.9 | 3.0 |
| qwen3.8-27b | 34.5 | 26.3 |

## 5. Kiểm chứng bằng người

Đã xuất phiếu chấm tay 30 cặp câu trả lời (ẩn tên hệ thống, đảo ngẫu nhiên vị trí A/B): `docs/phieu_cham_tay_cap_tra_loi.csv`. Người chấm điền điểm 1-5 cho A và B; đáp án ẩn nằm ở `docs/phieu_cham_tay_dap_an_an.json`. Sau khi có phiếu đã điền, chạy `python -m backend.evaluation.human_agreement` để tính mức đồng thuận giữa người và model chấm.

## Lưu ý

- Mỗi cấu hình dùng cỡ mẫu khác nhau (cấu hình chính lớn hơn) nên so sánh giữa các dòng chủ yếu nhìn hướng và độ lớn, không so từng con số.
- Model chấm khác họ với model sinh nhưng vẫn là LLM; chưa thay thế được người chấm.
