# Nguồn dữ liệu và giấy phép

Tài liệu này là sổ đăng ký các nguồn dữ liệu của Tea Scholar: nguồn nào đã dùng, giấy phép ra sao, nguồn nào đã xem xét nhưng chưa dùng và vì sao. Mọi nguồn ngoài phải có giấy phép rõ ràng, URL và ngày truy cập trước khi đưa vào cơ sở tri thức.

## 1. Nguồn đang dùng trong cơ sở tri thức

| Mã dataset | Nguồn | Số chunk | Giấy phép / tình trạng |
|---|---|---|---|
| `TL1_Tea_Technical_Guideline` | Tài liệu kỹ thuật trồng và chăm sóc chè (TL1) | 95 | Tài liệu do nhóm dự án cung cấp từ trước; **chưa ghi nhận giấy phép** (cần xác nhận nếu công bố) |
| `LaiChau_Tea_Technical_Guideline` | Quyết định 450/QĐ-SNNMT Lai Châu 2025 | 45 | Văn bản hành chính của cơ quan nhà nước; thường không thuộc đối tượng bảo hộ quyền tác giả (Luật Sở hữu trí tuệ, Điều 15). Đây là hiểu biết chưa được kiểm chứng pháp lý |
| `TeaLeafDiseaseBD` | Tài liệu mô tả bộ dữ liệu TeaLeafDiseaseBD (Bangladesh, 2025) | 22 | Xem giấy phép của bộ dữ liệu gốc; chỉ dùng phần mô tả |
| `FAO_EcoCrop_Camellia_sinensis` | [FAO EcoCrop — Camellia sinensis](https://ecocrop.apps.fao.org/ecocrop/srv/en/cropView?id=599) | 6 | **CC BY 4.0** theo điều khoản cơ sở dữ liệu của FAO; truy cập 19/09/2026. Phải ghi nguồn và không nêu FAO bảo trợ |
| `Tang2020_Tea_Nutrient_QUEFTS` | [Tang và cộng sự (2020), Scientific Reports](https://pmc.ncbi.nlm.nih.gov/articles/PMC7000836/), DOI 10.1038/s41598-020-57809-x | 3 | **CC BY 4.0**; truy cập 19/09/2026 |

Tổng: **171 chunk** (`tea_000001`–`tea_000171`).

### Cách các nguồn ngoài được đưa vào

- Nội dung tiếng Việt là bản **dịch/tóm lược do người soạn**, không sao chép nguyên văn dài. Mỗi chunk giữ `original_quote` (trích nguyên văn tiếng Anh) để kiểm tra bản dịch; giấy phép và URL nằm trong metadata của chunk và mô tả tài liệu trong bảng `documents`.
- Nguồn ngoài mang nhãn `source_type = scientific_reference`. Số liệu của các nguồn này là **số liệu quốc tế** (EcoCrop) hoặc **từ Trung Quốc** (Tang 2020); mỗi chunk nhắc nhở điều này và không thay thế định mức trong tài liệu kỹ thuật Việt Nam.
- Số liệu chỉ lấy từ những gì đã đọc trực tiếp trên nguồn ở ngày truy cập. Không có giá trị nào (ví dụ pH đất, lượng mưa tối ưu) được suy diễn thêm.
- Quy trình: `python scripts/build_external_sources.py` → `python scripts/build_knowledge_base.py` → `python scripts/validate_knowledge_base.py` → `python database/seed.py` → `python -m rag.ingest`. `validate_knowledge_base.py` từ chối chunk nguồn ngoài thiếu giấy phép, URL hoặc trích nguyên văn.
- Sau khi thêm dữ liệu, chạy lại `python -m rag.evaluation.run_eval`; lần gần nhất (72 câu trong phạm vi) cho Hit@3 = 0,986, không suy giảm so với trước.

## 2. Dữ liệu do dự án xây dựng

| Tệp | Nội dung | Ghi chú |
|---|---|---|
| `data/tea_regions.json` | 12 vùng chè: tên, tỉnh, vĩ độ, kinh độ | Dùng để nhận diện vùng trong câu hỏi và tra tọa độ thời tiết (`backend/services/regions.py`, API `GET /api/v1/weather/regions`). Trường `area_ha`, `altitude_m` để trống vì chưa có nguồn. Tọa độ lấy từ cấu hình cũ, **chưa đối chiếu nguồn độc lập**; riêng Sơn La đã sửa vì cấu hình cũ dùng nhầm tọa độ Mộc Châu |
| `rag/evaluation/eval_set.json` | 84 câu hỏi đánh giá RAG | Do người soạn tự gán nhãn; xem hạn chế trong `RAG_EVALUATION.md` |

## 3. Mức bao phủ so với các nhóm chủ đề cần có

Đếm sơ bộ bằng từ khóa trên 140 chunk kỹ thuật gốc (TL1 + Lai Châu); con số chỉ mang tính ước lượng, không phải đánh giá chất lượng nội dung.

| Nhóm | Bao phủ | Nhận xét |
|---|---|---|
| A. Giống chè | Khá | Có giống theo độ cao, vùng, tiêu chuẩn cây giống |
| B. Đất | **Yếu** | Có loại đất, độ dốc, cải tạo; **rất ít về pH, độ sâu tầng đất, thoát nước** |
| C. Trồng chè | Tốt | Thời vụ, mật độ, khoảng cách, hố trồng |
| D. Chăm sóc | Tốt | Tủ gốc, che bóng, tưới, làm cỏ |
| E. Bón phân | Tốt (N, P, K); **yếu (vi lượng)** | Có định mức theo tuổi và năng suất; thêm số liệu FAO/Tang 2020 làm đối chiếu quốc tế |
| F. Đốn chè | Tốt | Đốn phớt, lửng, đau, trẻ lại, thời vụ |
| G. Thu hái | Tốt | Hái tay, hái máy, mùa khô, bảo quản |
| H. Năng suất, chất lượng | Trung bình | Có yếu tố khí hậu và mô hình CSA; thiếu phân tích tuổi cây, độ ẩm theo chất lượng |
| Lá vàng, thiếu dinh dưỡng | **Chưa có** | Chưa tìm được nguồn truy cập mở có mô tả triệu chứng |

## 4. Nguồn đã xem xét nhưng chưa dùng

| Nguồn | Lý do chưa dùng |
|---|---|
| **NASA POWER** | Chưa cần: thời tiết hiện tại lấy từ Open-Meteo. Chỉ cần nếu muốn phân tích khí hậu lịch sử. Với đồ án nên chọn đúng một nguồn lịch sử (NASA POWER đơn giản hơn) |
| **ERA5 (Copernicus)** | Dữ liệu tái phân tích toàn cầu rất lớn (NetCDF/CSV, cần tài khoản CDS). Chưa cần cho hỏi đáp; để dành cho hướng phân tích khí hậu nâng cao |
| Bộ ảnh bệnh trên Kaggle (TeaLeafNet, Identifying Disease in Tea leaves…) | Giấy phép chưa kiểm tra; là dữ liệu ảnh, không dùng cho chatbot văn bản |
| **CS-D** (Assam, 81.000 ảnh, CC BY-NC, DOI 10.17632/94fzcdz8gz.1) | Là dữ liệu ảnh cho hướng chẩn đoán ảnh (ngoài phạm vi hiện tại) |
| Bài báo Zohora & Biswas (2025), Turkish J. Agric. Food Sci. Technol. | CC BY-NC 4.0; phần đọc được chỉ có khoảng hàm lượng dưỡng chất ở lá (Bangladesh), **không có mô tả triệu chứng thiếu dinh dưỡng** như cần thiết |
| Bài viết blog "Growing Teas" về pH và dinh dưỡng | Blog, không phải nguồn học thuật hay kỹ thuật chính thức; không dùng làm nguồn cho cơ sở tri thức |
| Bài báo của VAAS, Báo Nông nghiệp và Môi trường, Hiệp hội Chè | Nội dung có bản quyền; chỉ nên trích dẫn ngắn có nguồn hoặc xin phép |

## 5. Nguồn ứng viên đang chờ (cần bạn tải hoặc cho phép)

| Nguồn | Giá trị | Vướng mắc |
|---|---|---|
| Thông tư 75/2025/TT-BNNMT (danh mục thuốc BVTV được phép và cấm, hiệu lực 10/02/2026) | **Rất quan trọng:** tên thuốc trong tài liệu gốc (Genol, Lilacter…) có thể đã hết đăng ký | Phụ lục lớn, cần lọc phần dùng cho chè; trang thuvienphapluat chặn tải tự động |
| QCVN 01-132:2013/BNNPTNT (chè búp tươi an toàn thực phẩm) | Chuẩn quốc gia, chủ đề còn thiếu | Chưa xác minh còn hiệu lực |
| 10TCN 446:2001 (quy trình trồng, chăm sóc, thu hoạch chè) | Đối chiếu với TL1 | Chưa xem được nội dung và tình trạng hiệu lực; bản quyền tiêu chuẩn ngành chưa rõ |

## 6. Việc cần làm để lấp khoảng trống

1. Tìm nguồn nông học truy cập mở (hoặc xin phép tác giả/viện nghiên cứu) cho **đất (pH, độ sâu, thoát nước)**, **vi lượng** và **triệu chứng thiếu dinh dưỡng / lá vàng**.
2. Rà lại tên thuốc BVTV trong cơ sở tri thức so với Thông tư 75/2025.
3. Bổ sung `area_ha` và `altitude_m` cho `tea_regions.json` khi có nguồn thống kê chính thức.
4. Nhờ người khác viết câu hỏi kiểm tra độc lập để đánh giá RAG khách quan hơn.
