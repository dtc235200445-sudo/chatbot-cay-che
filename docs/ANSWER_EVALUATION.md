# Đánh giá chất lượng câu trả lời của chatbot

`RAG_EVALUATION.md` chỉ đo **truy xuất** (có tìm đúng tài liệu không). Tài liệu này đo **câu trả lời do LLM viết ra**: có bám tài liệu không, có trả lời đúng câu hỏi không, có từ chối đúng lúc không.

Tái lập:

```bash
python -m backend.evaluation.answer_eval --limit 24 --report docs/ANSWER_EVAL_RESULTS.md   # ~25 phút, gọi Groq
python -m backend.evaluation.export_review --generator openai/gpt-oss-120b --n 20          # phiếu chấm tay
python -m pytest backend/tests/test_answer_eval.py -q                                       # test các hàm chấm
```

## 1. Cách đo

Mỗi câu hỏi đi qua đúng luồng của hệ thống: truy xuất hybrid (bkai + BM25, top-3) → cổng liên quan → LLM sinh câu trả lời. Sau đó chấm hai lớp.

**Lớp xác định (không dùng LLM để chấm, nên đáng tin hơn)**

| Chỉ số | Cách đo |
|---|---|
| Từ chối đúng | Câu ngoài phạm vi (12 câu) phải bị từ chối; câu trong phạm vi không được từ chối nhầm |
| Số liệu có căn cứ | Mọi con số trong câu trả lời phải xuất hiện trong ngữ cảnh hoặc câu hỏi (bỏ mã chunk, nhãn nguồn, số thứ tự danh sách; "20 000" và "20.000" là một số) |

**Lớp LLM chấm.** Model chấm được yêu cầu tách câu trả lời thành các mệnh đề và chỉ dùng ngữ cảnh (không dùng kiến thức ngoài) để quyết định mệnh đề nào được chứng minh, cùng hai điểm 1–5:

- **Độ bám nguồn** = tỉ lệ mệnh đề được ngữ cảnh chứng minh.
- **Đúng câu hỏi** (1–5) và **đầy đủ** so với thông tin có trong ngữ cảnh (1–5).

**Chọn model.** Model chấm luôn khác model sinh, vì LLM có xu hướng chấm cao câu trả lời do chính nó viết:

| Model sinh | Model chấm |
|---|---|
| `openai/gpt-oss-120b` (đang dùng trong hệ thống) | `qwen/qwen3.8-27b` |
| `openai/gpt-oss-20b` | `qwen/qwen3.8-27b` |
| `qwen/qwen3.8-27b` | `openai/gpt-oss-120b` |

Mẫu: 24 câu trong phạm vi (lấy đều, tái lập được) + toàn bộ 12 câu ngoài phạm vi.

## 2. Kết quả

| Model sinh | Từ chối nhầm (/24) | Trả lời nhầm câu ngoài phạm vi (/12) | Độ bám nguồn | Đúng câu hỏi | Đầy đủ | Câu có số không căn cứ |
|---|---|---|---|---|---|---|
| gpt-oss-120b (chấm bởi qwen) | 0 | 0 | 0,977 | 4,83 | 4,21 | 1 |
| gpt-oss-20b (chấm bởi qwen) | 1 | 0 | 0,961 | 4,65 | 4,04 | 0 |
| qwen3.8-27b (chấm bởi gpt-oss-120b) | 0 | 0 | 0,984 | 4,83 | 4,75 | 1 |

Chi tiết từng mệnh đề bị chấm "không có căn cứ" nằm trong [ANSWER_EVAL_RESULTS.md](ANSWER_EVAL_RESULTS.md); dữ liệu thô ở `backend/evaluation/runs/`.

**Đọc kết quả thế nào:**

1. **Cả ba model đều bám nguồn tốt** (từ 0,96 trở lên theo cách chấm khắt khe) và không có model nào trả lời nhầm câu ngoài phạm vi. Phần lớn công lao là của cổng truy xuất: câu ngoài phạm vi bị chặn trước khi tới LLM.
2. **gpt-oss-120b nhỉnh hơn gpt-oss-20b** (cùng một model chấm nên so sánh được): bám nguồn 0,977 so với 0,961, đúng câu hỏi 4,83 so với 4,65, và 20b từ chối nhầm 1 câu trong phạm vi. Chênh lệch nhỏ và cỡ mẫu nhỏ, nhưng đủ để không có lý do đổi sang 20b.
3. **Không so sánh được qwen với hai model còn lại**: qwen được chấm bởi một model khác (gpt-oss-120b), mà hai model chấm cho điểm rộng/khắt khe khác nhau (ví dụ điểm "đầy đủ" 4,75 so với 4,21 có thể chỉ phản ánh độ dễ tính của người chấm). Để so sánh công bằng cần cùng một model chấm cho mọi model sinh, hoặc chấm chéo cả hai chiều.
4. **Chênh lệch giữa các model nằm trong khoảng nhiễu.** Mỗi câu có 3–8 mệnh đề, 24 câu tổng cộng chỉ có vài mệnh đề bị đánh dấu khác nhau; 0,977 và 0,984 không phân biệt được về mặt thống kê.

## 3. Độ tin cậy của model chấm (quan trọng)

Tôi đối chiếu tay các mệnh đề bị đánh dấu với tài liệu gốc:

| Mệnh đề bị đánh dấu | Sự thật | Model chấm |
|---|---|---|
| "Bt là *Bacillus thuringiensis*" (sâu chùm) | Tài liệu chỉ ghi "Bt", LLM thêm kiến thức ngoài | Đúng |
| "Nên bảo quản trên kệ, trong kho" (chè tươi) | Ý "kê cao" thuộc phần chè khô, LLM áp sang chè tươi | Đúng |
| "Ma, Ba chưa được ghi rõ tên đầy đủ" | Tài liệu chỉ liệt kê "Bt, Ma, Ba" | Nhập nhằng |
| "Nhóm I và II nguy cơ cao nhất" | Tài liệu: Nhóm I rất độc, Nhóm II độc cao | Báo động giả (diễn đạt lại đúng) |
| "Tài liệu không nêu ngày ký" | Nói về sự vắng mặt của thông tin | Báo động giả |
| "Trồng ở độ cao 1.800 m và dưới" | Tài liệu: "lên đến khoảng 1.800 m" | Báo động giả (khác sắc thái) |

Trong 6 mệnh đề tôi kiểm tra có 2 đúng, 1 nhập nhằng, 3 báo động giả. **Model chấm nghiêng về khắt khe**, nên điểm bám nguồn ở trên nhiều khả năng **thấp hơn** thực tế. Chỉ 6 mẫu nên đây chưa phải số đo độ chính xác, chỉ là dấu hiệu cần kiểm tra kỹ hơn. Cách làm đúng: chấm tay 20 câu trong `docs/answer_review_sheet.md` rồi tính tỉ lệ khớp giữa người và model chấm (từ khoảng 85% trở lên thì có thể tin số tự động).

## 4. Điều thực sự học được về chatbot

Các lỗi thật tìm thấy (nhỏ nhưng có thật):

- **Thêm kiến thức ngoài tài liệu** (giải nghĩa "Bt" thành *Bacillus thuringiensis*).
- **Dùng sai ngữ cảnh**: lấy hướng dẫn bảo quản chè khô áp cho chè tươi.
- **Diễn giải thêm mục đích** ("đốn phớt để giữ độ che phủ") dù prompt đã cấm; LLM tuân thủ chưa hoàn toàn.

Chưa có lỗi nghiêm trọng nào như số liệu bịa hoàn toàn: lớp kiểm số tự động chỉ báo 1 câu ở mỗi model (đều là số đếm phụ như "4 nhóm", "2 loại").

## 5. Hạn chế

- **Mẫu nhỏ** (24 câu trong phạm vi) và chưa chấm tay nên mọi con số cần hiểu là ước lượng.
- **Câu hỏi trong bộ đánh giá do người soạn và có từ ngữ gần tiêu đề chunk**, dễ hơn câu hỏi thực tế của người dùng.
- Chỉ đo câu hỏi một lượt; chưa đo hội thoại nhiều lượt và câu hỏi kết hợp thời tiết.
- Model chấm khắt khe và nhiễu (mục 3); không nên dùng điểm tự động để kết luận về từng mệnh đề.
- Model chấm có thể khác nhau giữa các lần chạy dù nhiệt độ bằng 0 (nhà cung cấp không cam kết kết quả xác định).
- Mỗi lần chạy đầy đủ tốn khoảng 25 phút và vài trăm lượt gọi Groq; giới hạn tần suất của gói miễn phí làm chạy chậm.

## 5b. Hình thức câu trả lời (độ dài, cấu trúc, chép nguyên văn)

Người dùng phản ánh câu trả lời đôi khi là một đoạn văn dài gần như chép lại tài liệu. Bộ đánh giá được bổ sung các chỉ số hình thức xác định (không dùng LLM chấm): số từ, có cấu trúc (gạch đầu dòng, đánh số, bảng, tiêu đề in đậm), tỉ lệ cụm 6 từ trùng nguyên văn với tài liệu (`copy_ratio`), và ghi mã nguồn hoặc phần "Lưu ý" thừa trong nội dung.

Thay đổi: viết lại `SYSTEM_PROMPT` với phần "cách trình bày" (mở bằng một câu ý chính; định dạng theo loại câu hỏi: khái niệm dùng văn xuôi 2–3 câu, triệu chứng và biện pháp dùng gạch đầu dòng ngắn, quy trình đánh số, so sánh nhiều mức dùng bảng; dưới 120 từ; không ghi mã nguồn hay "Lưu ý"), cho phép trả lời một phần thay vì từ chối hẳn, hạ nhiệt độ 0,3 xuống 0,2.

Đo trên `gpt-oss-20b`, 24 câu trong phạm vi, cùng cách tính (`gpt-oss-120b` chưa đo được vì hết hạn mức token trong ngày của tài khoản Groq):

| Chỉ số | Prompt cũ | Prompt mới, suy luận `low` | Prompt mới, suy luận `medium` (đang dùng) |
|---|---|---|---|
| Số từ trung bình | 81 | 85 | **67** |
| Câu trên 150 từ | 3 | 4 | **0** |
| Có cấu trúc | 86% | 83% | **88%** |
| Ghi mã nguồn / "Lưu ý" thừa | 1 | 0 | **0** |
| Chép nguyên văn (trung bình) | 0,18 | 0,20 | 0,21 |
| Câu trả lời rỗng | 1 | 0 | 0 |
| Từ chối nhầm câu trong phạm vi | 1 | 0 | 0 |

**Kết luận.** Chép nguyên văn không phải vấn đề phổ biến (trung bình 0,18; hai trong 24 câu ≥ 0,4 là một bảng phân loại và một câu ngắn hợp lý); vấn đề thật là độ dài và tính nhất quán của cách trình bày, và prompt mới cải thiện cả hai. Suy luận mức `low` làm câu trả lời dài dòng hơn (kém tuân thủ quy tắc độ dài) nên chọn `medium`.

**Lỗi phát hiện thêm khi đo:** model suy luận tính cả token "suy nghĩ" vào `max_tokens`; với giới hạn cũ 600, một câu cần 463–677 token nên đôi khi bị cắt thành **câu trả lời rỗng**. Đã tăng lên 1200, thử lại một lần khi rỗng, và báo lỗi 502 nếu vẫn rỗng.

**Chưa kiểm chứng:** độ bám nguồn sau khi đổi prompt (cần chạy lại model chấm, tốn hạn mức token); kết quả trên `gpt-oss-120b` (model đang dùng thật); mẫu 24 câu nên chênh lệch nhỏ nằm trong nhiễu.

**Lưu ý hạn mức:** gói miễn phí của Groq giới hạn 200.000 token/ngày cho mỗi model. Một lần chạy đánh giá đầy đủ (ba model, có chấm) tiêu tốn phần lớn hạn mức này và làm chatbot báo "hết hạn mức" cho tới khi hồi lại.

## 6. Hướng cải thiện tiếp theo

1. Chấm tay 20 phiếu để hiệu chỉnh model chấm.
2. Thêm bộ câu hỏi độc lập do người khác soạn.
3. Nếu muốn giảm lỗi "thêm kiến thức ngoài", thử yêu cầu LLM trích dẫn nguyên văn từng ý (dạng `[tea_000154]`) và tự kiểm tra trích dẫn có nằm trong ngữ cảnh không.
