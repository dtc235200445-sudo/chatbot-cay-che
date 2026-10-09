# Kết quả đánh giá Answer trên mẫu 150 câu (bộ 1000 câu)

Chạy lúc 23/09/2026 19:22. Model sinh: `openai/gpt-oss-120b` (đang dùng thật trong sản phẩm). Model chấm: `qwen/qwen3.8-27b` (khác model sinh). Nguồn mẫu: `E:\NHÁP 2\tea_chatbot_qa_test_1000.jsonl`.

## 1. An toàn / Abstention (24 câu `abstain_no_data`, dữ liệu vùng chè không có sẵn)

| N | Từ chối đúng | Vi phạm (tự bịa số liệu) |
|---|---|---|
| 24 | 24 | 0 |

## 2. Câu hỏi ngoài phạm vi RAG hiện tại (36 câu region_fact/coordinate/boolean)

Nguồn Tea_Regions_Project_Config không được ingest vào RAG; kỳ vọng từ chối vì ngoài phạm vi RAG hiện tại.

| N | Từ chối / không liên quan |
|---|---|
| 6 | 5 |

## 3. Chất lượng câu trả lời (semantic_factual, có ground-truth)

| N | Từ chối nhầm | Đã chấm | Faithfulness | **Answer Correctness (1-5)** | Relevance (1-5) | **Key point coverage** | Số liệu không căn cứ |
|---|---|---|---|---|---|---|---|
| 120 | 9 | 104 | 0.994 | 4.74 | 4.99 | 0.947 | 1 |

Độ trễ trung bình (câu có gọi LLM): 14.36s

## Theo question_type (semantic_factual)

| question_type | N | Correctness | Faithfulness | Key point coverage |
|---|---|---|---|---|
| completeness | 17 | 4.76 | 1.000 | 0.962 |
| direct_grounded | 20 | 4.70 | 0.975 | 0.963 |
| domain_question | 20 | 4.90 | 0.995 | 1.000 |
| numeric_extraction | 7 | 4.57 | 1.000 | 0.837 |
| paraphrase | 19 | 4.89 | 1.000 | 0.972 |
| source_constrained | 21 | 4.52 | 1.000 | 0.884 |

## Hạn chế của lần chạy này

**8/150 câu (5.3%) chưa đánh giá được** sau 3 lượt chạy lại, vì cạn hạn mức Groq trong ngày cho model
`openai/gpt-oss-120b` (200.000 token/ngày). Không có nhà cung cấp dự phòng nào được cấu hình trong `.env`
(`LLM_FALLBACKS` rỗng) nên không tự chuyển sang model khác được. Số liệu ở trên tính trên 142/150 câu
(94.7%) thực sự đánh giá được — không phải lỗi chất lượng model, chỉ là thiếu dữ liệu cho 8 câu này.
Chạy lại khi quota hồi phục (khuyến nghị: chờ sang ngày hôm sau) bằng:
`python -m backend.evaluation.qa1000_repair_failed`.

Câu còn thiếu: QA0205, QA0245, QA0685, QA0765, QA0992, QA0857, QA0889, QA0874
(2 completeness core-RAG, 1 numeric_extraction, 5 câu vùng chè region_* — nhóm này vốn đã ngoài phạm vi
RAG hiện tại nên không ảnh hưởng tới kết luận về chất lượng RAG chính).
