# So sánh Tea AI với RAG thường (tầng câu trả lời)

Cùng model sinh `openai/gpt-oss-120b` (cùng temperature 0.2, max_tokens, reasoning_effort như sản phẩm), cùng model chấm `qwen/qwen3.8-27b` và cùng prompt chấm. Khác nhau: **Tea AI** = hybrid retrieval + cổng từ chối + prompt ràng buộc của sản phẩm; **RAG thường** = embedding đa ngữ dense top-3 + prompt chung ("trả lời dựa trên ngữ cảnh, nếu không có thì nói không biết"), không cổng.

Tập con ghép cặp: 55 câu có kết quả ở cả hai hệ thống (24 câu thiếu dữ liệu, 31 câu có đáp án chuẩn; 19 câu được chấm ở cả hai).


## 1. Câu thiếu dữ liệu (abstain_no_data): có từ chối đúng, không bịa số liệu không

| Hệ thống | N | Từ chối đúng | Bịa số liệu | Cổng từ chối được kích hoạt |
|---|---|---|---|---|
| Tea AI | 24 | 24 | 0 | 0/24 |
| RAG thường | 24 | 24 | 0 | không có cổng |

## 2. Chất lượng câu trả lời (câu có đáp án chuẩn, chỉ tính câu cả hai đều được chấm)

| Hệ thống | N chấm | Correctness (1-5) | Faithfulness | Key point coverage | Số liệu không căn cứ | Độ trễ TB (s) |
|---|---|---|---|---|---|---|
| Tea AI | 19 | 4.63 | 0.995 | 0.902 | 0 | 34.6 |
| RAG thường | 19 | 3.21 | 0.917 | 0.551 | 3 | 9.9 |

Chênh lệch ghép cặp (Tea AI − RAG thường), khoảng tin cậy 95% bằng bootstrap:

| Chỉ số | Chênh lệch | KTC 95% |
|---|---|---|
| Correctness | 1.421 | [+0.736, +2.158] |
| Faithfulness | 0.078 | [+0.010, +0.184] |
| Key point coverage | 0.352 | [+0.136, +0.576] |

### Theo loại câu hỏi (Correctness / Key point coverage)

| Loại | N | Tea AI | RAG thường |
|---|---|---|---|
| completeness | 4 | 4.75 / 0.972 | 3.00 / 0.438 |
| direct_grounded | 3 | 4.33 / 0.800 | 3.67 / 0.600 |
| domain_question | 5 | 4.80 / 1.000 | 2.60 / 0.382 |
| numeric_extraction | 4 | 4.25 / 0.714 | 3.75 / 0.750 |
| paraphrase | 3 | 5.00 / 1.000 | 3.33 / 0.667 |

## 3. Từ chối nhầm và truy xuất trúng nguồn (câu có đáp án chuẩn)

| Hệ thống | N | Từ chối nhầm | Top-3 chứa đúng chunk nguồn |
|---|---|---|---|
| Tea AI | 31 | 0 | (xem `QA1000_RETRIEVAL_RESULTS.md`: Hit@3 0.991) |
| RAG thường | 31 | 12 | 12/31 |

## Lưu ý

- Tập con nhỏ (chọn đều theo từng loại, không ngẫu nhiên hoàn toàn): dùng để nhìn xu hướng, KTC rộng, không nên coi là kết luận thống kê chắc chắn.
- Cùng một model chấm cho cả hai hệ thống; model chấm có thể có thiên lệch riêng (độ tin cậy của model chấm xem `ANSWER_EVAL_RESULTS.md`).
- "Từ chối" được nhận diện bằng cùng một bộ luật rộng cho cả hai hệ thống (câu ngắn nói không có/không biết).
