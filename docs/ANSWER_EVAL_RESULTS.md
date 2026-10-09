# Kết quả đánh giá chất lượng câu trả lời

Chạy lúc 20/09/2026 15:20. Truy xuất: hybrid (bkai + BM25), top-3. Model chấm luôn khác model sinh. Dữ liệu thô: `backend/evaluation/runs/`.

| Model sinh | Model chấm | Câu trong phạm vi | Từ chối nhầm | Câu ngoài phạm vi | Trả lời nhầm | Độ bám nguồn | Đúng câu hỏi (1-5) | Đầy đủ (1-5) | Có số liệu không căn cứ | Độ trễ TB (s) |
|---|---|---|---|---|---|---|---|---|---|---|
| openai/gpt-oss-120b | qwen/qwen3.8-27b | 24 | 0 | 12 | 0 | 0.977 | 4.83 | 4.21 | 1 | 1.8 |
| openai/gpt-oss-20b | qwen/qwen3.8-27b | 24 | 1 | 12 | 0 | 0.961 | 4.65 | 4.04 | 0 | 1.3 |
| qwen/qwen3.8-27b | openai/gpt-oss-120b | 24 | 0 | 12 | 0 | 0.984 | 4.83 | 4.75 | 1 | 1.1 |

Độ bám nguồn = tỉ lệ mệnh đề được ngữ cảnh chứng minh (trung bình theo câu). "Số liệu không căn cứ" = số câu trả lời có con số không xuất hiện trong ngữ cảnh hay câu hỏi.

## Mệnh đề bị chấm "không có căn cứ" — openai/gpt-oss-120b (chấm bởi qwen/qwen3.8-27b)

- **q013** — Sâu chùm hại chè
  - mệnh đề: Bt là Bacillus thuringiensis.
  - mệnh đề: Ma là một loại thuốc chưa được ghi rõ tên đầy đủ trong tài liệu.
  - mệnh đề: Ba là một loại thuốc chưa được ghi rõ tên đầy đủ trong tài liệu.
- **q022** — Chè nên trồng trên loại đất nào?
  - số không có trong ngữ cảnh: 4
- **q025** — Mật độ trồng chè là bao nhiêu cây trên một ha?
  - mệnh đề: Ở vùng đất có độ cao > 500m, các giống PH12, PH14, Shan Chất Tiền, TB14 có mật độ trồng 13.000 cây/ha.
- **q052** — Bảo quản chè búp tươi sau khi hái
  - mệnh đề: Nên bảo quản trên kệ, trong kho
- **q064** — Sâu hại chính trên cây chè
  - mệnh đề: Các biện pháp phòng trừ cho cả hai loại sâu đều bao gồm bắt sâu non, làm cỏ, xới xáo quanh gốc để diệt nhộng và phun thuốc trừ sâu (Bt, Ma, Ba, Actara 25WG, Trebon 10EC/20WP/30EC).

## Mệnh đề bị chấm "không có căn cứ" — openai/gpt-oss-20b (chấm bởi qwen/qwen3.8-27b)

- **q019** — Thuốc BVTV được phân loại theo độ độc như thế nào?
  - mệnh đề: Nhóm I và II được xem là các loại thuốc có nguy cơ cao nhất.
- **q052** — Bảo quản chè búp tươi sau khi hái
  - mệnh đề: Thường xuyên đảo chè để tránh chảy nước và giữ độ ẩm đồng đều.
  - mệnh đề: Đặt chè cao cách mặt đất tối thiểu 20 cm (đối với chè khô, nhưng cũng áp dụng khi cần tránh ẩm).
- **q079** — Chè trồng được ở độ cao tối đa bao nhiêu mét?
  - mệnh đề: Chè thường được trồng ở độ cao 1.800 m và dưới

## Mệnh đề bị chấm "không có căn cứ" — qwen/qwen3.8-27b (chấm bởi openai/gpt-oss-120b)

- **q013** — Sâu chùm hại chè
  - số không có trong ngữ cảnh: 2
- **q052** — Bảo quản chè búp tươi sau khi hái
  - mệnh đề: Bạn nên tuân thủ mức thời gian ngắn hơn (8 giờ) để đảm bảo an toàn chất lượng.
- **q061** — Quyết định ban hành hướng dẫn kỹ thuật trồng chè có hiệu lực từ khi nào?
  - mệnh đề: Tài liệu không nêu cụ thể ngày tháng năm ký chính xác của Quyết định mới này.

