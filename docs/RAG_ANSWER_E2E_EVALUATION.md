# Đánh giá câu trả lời và end-to-end: Tea AI so với RAG thường

Model sinh `openai/gpt-oss-120b`, model chấm `qwen/qwen3.8-27b` (khác họ). Bộ câu có đáp án: **114 câu** semantic_factual thuộc kho RAG (mẫu 150 câu của bộ 1000 câu), không lọc theo kết quả của hệ thống nào.

## 1. Tầng câu trả lời

| Chỉ số | Tea AI | RAG thường | Chênh lệch Tea − RAG thường [KTC 95%] |
|---|---|---|---|
| Faithfulness (chỉ câu không từ chối) | 0.994 (n=104) | 0.866 (n=69) | +0.141 [+0.073, +0.217], 61 cặp |
| Response Relevancy | 0.497 (n=114) | 0.278 (n=114) | +0.219 [+0.160, +0.279], 114 cặp |
| Factual Correctness: Precision (chỉ câu không từ chối) | 0.926 (n=104) | 0.363 (n=69) | +0.516 [+0.413, +0.615], 61 cặp |
| Factual Correctness: Recall | 0.869 (n=114) | 0.260 (n=114) | +0.608 [+0.511, +0.696], 114 cặp |
| Factual Correctness: F1 | 0.884 (n=109) | 0.228 (n=114) | +0.646 [+0.557, +0.728], 109 cặp |

Câu bị từ chối nhầm: Response Relevancy = 0, Factual Correctness Recall/F1 = 0; không có mệnh đề nên không tính Faithfulness và Precision (số n cho biết số câu được tính).

## 2. End-to-end

### 2.1. Độ chính xác câu trả lời

| Chỉ số | Tea AI | RAG thường |
|---|---|---|
| Trả lời đúng | 78.9% | 21.9% |
| Đúng hoặc đúng một phần | 90.4% | 25.4% |
| Từ chối nhầm câu có đáp án | 5/114 | 45/114 |

Chênh lệch tỉ lệ trả lời đúng: +57.0 điểm phần trăm [KTC 95% +46.5, +67.5].

### 2.2. Khi tài liệu không có thông tin (No-answer accuracy)

| Bộ câu | Tea AI: từ chối đúng | Tea AI: bịa số | RAG thường: từ chối đúng | RAG thường: bịa số |
|---|---|---|---|---|
| 24 câu thiếu dữ liệu (vùng chè) | 24/24 | 0 | 24/24 | 0 |
| 12 câu ngoài phạm vi (eval_set.json) | 12/12 | 0 | 12/12 | 0 |
| **Tổng** | **36/36** | | **36/36** | |

"Bịa số" = không từ chối mà câu trả lời có số liệu cụ thể.

### 2.3. Thời gian chờ và chi phí mỗi câu hỏi

Chạy lại toàn bộ luồng trên 20 câu, gọi API Groq thật. Giá gpt-oss-120b trên Groq: $0.15/1 triệu token vào, $0.6/1 triệu token ra (token ra gồm cả phần suy luận của model).

| Chỉ số | Tea AI | RAG thường |
|---|---|---|
| Truy xuất, trung vị (ms) | 62 | 31 |
| LLM, trung vị (giây) | 1.72 | 1.88 |
| Tổng, trung vị (giây) | 1.80 | 1.90 |
| Tổng, P90 (giây) | 3.09 | 3.11 |
| Token vào, trung bình | 1557 | 680 |
| Token ra, trung bình | 511 | 642 |
| Chi phí mỗi câu (USD) | 0.00054 | 0.00049 |
| Chi phí 1.000 câu (USD) | 0.54 | 0.49 |

Thời gian LLM phụ thuộc tải của Groq tại lúc đo; nên so sánh hai hệ thống trong cùng lượt chạy, không đọc như con số cố định. Chi phí chưa gồm model chấm (chỉ dùng khi đánh giá).

### 2.4. Người chấm (Human evaluation)

Chưa có kết quả. Phiếu `docs/phieu_cham_tay_cap_tra_loi.csv` (30 cặp, ẩn tên hệ thống: A/B) chưa được điền. Sau khi điền, chạy `python -m backend.evaluation.human_agreement` để có điểm theo người và mức đồng thuận với model chấm.

## 3. Theo loại câu hỏi (Factual Correctness F1 / Faithfulness)

| Loại | N | Tea AI | RAG thường |
|---|---|---|---|
| completeness | 21 | 0.93 / 1.00 | 0.21 / 1.00 |
| direct_grounded | 21 | 0.90 / 0.97 | 0.33 / 0.92 |
| domain_question | 21 | 0.91 / 0.99 | 0.18 / 0.64 |
| numeric_extraction | 9 | 0.75 / 1.00 | 0.29 / 0.97 |
| paraphrase | 21 | 0.85 / 1.00 | 0.22 / 0.91 |
| source_constrained | 21 | 0.89 / 1.00 | 0.18 / 0.83 |

## Lưu ý khi diễn giải

- Các chỉ số làm theo định nghĩa của Ragas nhưng do một model chấm duy nhất thực hiện; chưa đối chiếu với người chấm.
- Faithfulness chỉ đo câu trả lời có bám ngữ cảnh không. RAG thường lấy sai tài liệu nhưng vẫn có thể có Faithfulness cao (bám đúng tài liệu sai), vì vậy cần đọc cùng Factual Correctness.
- Câu trả lời của Tea AI được sinh ngày 23/09; ngữ cảnh được truy xuất lại khi chấm (truy xuất tất định, kho không đổi).
- Giữa chừng, prompt chấm được sửa để model chấm ghi mệnh đề ngắn và gộp tối đa 15 mệnh đề/câu (Groq giới hạn 1.000 token ra mỗi phút làm kết quả chấm của câu trả lời dài bị cắt cụt). Khoảng 150/228 câu được chấm bằng prompt cũ; các chỉ số là tỉ lệ nên ảnh hưởng nhỏ, nhưng câu trả lời rất dài có thể bị chấm thô hơn.
- Mẫu có đáp án là mẫu con 150 câu của bộ 1000 câu, được sinh từ chính tài liệu nên thuận lợi cho khâu truy xuất.
