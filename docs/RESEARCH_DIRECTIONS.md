# Hướng nghiên cứu kết hợp với dự án

Tài liệu này đề xuất các hướng nghiên cứu có thể làm tiếp trên nền Tea Scholar, dựa trên **những gì đã đo được** (không dựa trên mong muốn). Mỗi hướng ghi rõ: câu hỏi nghiên cứu, kỹ thuật, cách đo, hạ tầng đã có, chi phí và rủi ro.

## Câu chuyện đề xuất cho luận văn

> **Xây dựng chatbot RAG tiếng Việt đáng tin cậy cho nông nghiệp: truy xuất bền với cách gõ thực tế, từ chối đúng khi thiếu tri thức, và câu trả lời kiểm chứng được.**

Ba trụ cột khớp với ba kết quả thực nghiệm đã có, nên câu chuyện có bằng chứng thay vì chỉ mô tả hệ thống:

| Trụ cột | Vấn đề đã đo được | Đã làm | Còn để nghiên cứu |
|---|---|---|---|
| **A. Truy xuất bền** | Gõ không dấu làm Hit@3 rơi 0,986 xuống 0,361 | BM25 bỏ dấu + chỉ mục vector bỏ dấu: Hit@3 = 0,944 (`RAG_EVALUATION.md` mục 3c) | Gõ nhầm, viết tắt, từ địa phương; so sánh các phương pháp chuẩn hóa |
| **B. Từ chối đúng** | Cổng cosine cũ chỉ từ chối 58% câu ngoài phạm vi | Đổi model embedding tiếng Việt: 100% (mẫu nhỏ) | Hiệu chỉnh có bảo đảm thống kê, bộ câu ngoài phạm vi lớn hơn |
| **C. Câu trả lời kiểm chứng được** | LLM thêm kiến thức ngoài tài liệu, dùng nhầm ngữ cảnh | Bộ đánh giá bám nguồn (`ANSWER_EVALUATION.md`) | Kiểm chứng từng mệnh đề, lọc mệnh đề không có căn cứ |

## Các hướng cụ thể

### Hướng 1 — Độ bền truy xuất tiếng Việt (nên làm, đã có kết quả mở đầu)

- **Câu hỏi:** phương pháp chuẩn hóa nào giữ chất lượng truy xuất khi người dùng gõ không dấu / gõ nhầm?
- **Kỹ thuật so sánh:** (a) không xử lý; (b) BM25 bỏ dấu; (c) khôi phục dấu bằng công cụ (pyvi kém, thử thêm mô hình khôi phục dấu khác hoặc dùng LLM); (d) chỉ mục vector song song có dấu/bỏ dấu (đang dùng); (e) sửa chính tả trước truy xuất; (f) model embedding được huấn luyện thêm với dữ liệu không dấu.
- **Đo:** Hit@k, MRR, tỉ lệ cổng nhận/từ chối, theo từng loại nhiễu. Dùng `python -m rag.evaluation.robustness`.
- **Hạ tầng đã có:** phép thử độ bền, bộ 84 câu, retriever có chế độ vector/BM25/hybrid.
- **Chi phí:** thấp. **Rủi ro:** ít; điểm yếu là bộ câu hỏi do một người soạn.
- **Vì sao đáng làm:** vấn đề có thật, đã có số liệu trước/sau, ít nghiên cứu tiếng Việt cho lĩnh vực nông nghiệp.

### Hướng 2 — Từ chối có bảo đảm (abstention) với hiệu chỉnh thống kê

- **Câu hỏi:** làm sao chọn ngưỡng từ chối có bảo đảm tỉ lệ nhận nhầm/từ chối nhầm, thay vì chọn tay trên 12 câu?
- **Kỹ thuật:** sinh thêm vài trăm câu ngoài phạm vi (nhờ LLM rồi người kiểm tra), so sánh cổng ngưỡng đơn / hai tín hiệu (cosine + BM25) / bộ phân loại học từ đặc trưng; ước lượng khoảng tin cậy (bootstrap) hoặc dự đoán phù hợp (conformal prediction).
- **Đo:** AUROC, tỉ lệ nhận/từ chối tại ngưỡng, khoảng tin cậy.
- **Chi phí:** trung bình (chủ yếu tạo và kiểm dữ liệu ngoài phạm vi). **Rủi ro:** cần kiểm tra tay để dữ liệu sinh không nhiễm.

### Hướng 3 — Câu trả lời kiểm chứng được (attribution / bám nguồn)

- **Câu hỏi:** yêu cầu LLM trích dẫn từng ý, rồi tự kiểm tra trích dẫn, có giảm mệnh đề không có căn cứ không?
- **Kỹ thuật:** (a) prompt bắt buộc trích `[tea_000154]` cho mỗi ý; (b) kiểm tra tự động: mọi trích dẫn phải trỏ tới chunk đã truy xuất, số liệu phải có trong chunk; (c) lọc hoặc gắn cờ mệnh đề không được chứng minh; (d) so sánh các model sinh.
- **Đo:** độ bám nguồn (bộ đánh giá đã có), tỉ lệ mệnh đề bị lọc, độ đầy đủ.
- **Điều kiện cần:** hiệu chỉnh model chấm bằng chấm tay (`docs/answer_review_sheet.md`); hiện model chấm có nhiều báo động giả.
- **Chi phí:** trung bình; tốn lượt gọi Groq. **Rủi ro:** lọc quá tay làm câu trả lời cụt.

### Hướng 4 — RAG kết hợp dữ liệu có cấu trúc (thời tiết + tri thức)

- **Câu hỏi:** kết hợp thời tiết thực tế với ngưỡng trong tài liệu có cho khuyến nghị đúng hơn LLM tự suy luận không?
- **Kỹ thuật:** trích ngưỡng thành quy tắc có nguồn (ví dụ nhiệt độ 18–28°C, độ ẩm 75–80% từ `tea_000053`, `tea_000121`), để quy tắc quyết định đánh giá, LLM chỉ diễn đạt; so với LLM tự đánh giá (đã thấy LLM tự gọi 70% là "cao" khi tài liệu không nói vậy).
- **Đo:** bộ kịch bản (thời tiết + câu hỏi) có nhãn đúng do chuyên gia gán; tỉ lệ đánh giá sai.
- **Hạ tầng đã có:** trang thời tiết đối chiếu ngưỡng, luồng câu hỏi lai. **Rủi ro:** cần chuyên gia nông nghiệp gán nhãn; ngưỡng giữa hai tài liệu mâu thuẫn (TL1 nói 18–28°C, Lai Châu nói 15–20°C).

### Hướng 5 — Chẩn đoán bệnh qua ảnh kết hợp RAG (đa phương thức)

- **Câu hỏi:** phân loại bệnh từ ảnh lá rồi lấy tri thức xử lý từ RAG có hữu ích hơn hỏi bằng chữ không?
- **Kỹ thuật:** tinh chỉnh mô hình ảnh nhỏ (transfer learning) trên bộ CS-D (CC BY-NC, 81.000 ảnh, 6 lớp) rồi truyền tên bệnh vào truy xuất tri thức.
- **Chi phí: cao** (tải dữ liệu lớn, cần GPU hoặc chạy lâu). **Rủi ro:** ảnh Ấn Độ lệch so với chè Việt Nam; tên bệnh tiếng Anh cần ánh xạ sang thuật ngữ tiếng Việt trong cơ sở tri thức (hiện tên bệnh trong DB còn lệch). Nên làm sau nếu còn thời gian; tận dụng được `tea_regions`/RAG hiện có.

### Hướng 6 — Nghiên cứu độ tin cậy của LLM làm người chấm

- **Câu hỏi:** model chấm tự động khớp với người đến đâu trong lĩnh vực nông nghiệp tiếng Việt?
- **Đã có:** ba model, phiếu chấm tay, và quan sát ban đầu (3/6 mệnh đề bị đánh dấu là báo động giả).
- **Cần:** 20–50 phiếu chấm tay, tính tỉ lệ khớp và hệ số Cohen's kappa. Ít tốn kém, đóng góp về phương pháp luận.

### Các hướng nên cân nhắc kỹ trước khi làm

- **Cross-encoder rerank, HyDE, multi-query** từ RAG-pipeline-visualizer: Hit@3 đã 0,986 nên dư địa nhỏ; chỉ nên làm như một khảo sát ablation có số liệu, không phải đóng góp chính.
- **Fine-tune model embedding** với dữ liệu chè: cần nhiều cặp câu hỏi–đoạn tài liệu có nhãn (hiện chỉ 84 câu), dễ overfit.
- **Bảng "quản trị dữ liệu" tự động** (thu thập tài liệu mới): giá trị kỹ thuật nhưng ít tính nghiên cứu.

## Thứ tự đề xuất

1. **Hướng 1** (đã có nền, ra kết quả nhanh) làm chương thực nghiệm đầu tiên.
2. **Hướng 6** (rất rẻ) để lấy được độ tin cậy cho phần đánh giá câu trả lời.
3. **Hướng 3** hoặc **Hướng 2** tùy bạn muốn nhấn vào độ đáng tin của câu trả lời hay bảo đảm từ chối.
4. Hướng 4 và 5 nếu còn thời gian và có chuyên gia hỗ trợ gán nhãn.

## Những điều cần làm trước khi công bố kết quả

- **Bộ đánh giá độc lập:** hiện toàn bộ do một người soạn, gần với từ ngữ tiêu đề chunk; cần thêm 30–50 câu do người khác viết.
- **Khoảng tin cậy:** với 72 câu, chênh 0,02 chỉ là 1–2 câu; báo cáo bootstrap thay cho một con số.
- **Tách dữ liệu chọn tham số và dữ liệu kiểm tra** (ngưỡng, trọng số hiện chọn trên chính bộ đánh giá).
- **Nêu rõ giới hạn:** cơ sở tri thức nhỏ (171 đoạn), một lĩnh vực, ba tài liệu gốc.
