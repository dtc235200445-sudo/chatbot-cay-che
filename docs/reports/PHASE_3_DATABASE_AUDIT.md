# PHASE 3 — DATABASE AUDIT REPORT

## 1. Executive Summary

Trước khi bắt đầu thiết kế và triển khai Phase 3, chúng tôi đã thực hiện Audit toàn bộ cấu trúc dự án **Tea Scholar AI** để đánh giá hiện trạng cơ sở dữ liệu.

* **Trạng thái Database hiện tại:** Chưa có bất kỳ Database engine (SQLite/PostgreSQL/MySQL) hay file cơ sở dữ liệu nào được khởi tạo trong dự án.
* **Thư viện ORM hiện có:** Môi trường Python 3.12 của hệ thống đã có sẵn package **SQLAlchemy (v2.0)** và **Alembic**, chưa có bất kỳ mô hình bảng (`models`) hay file cấu hình migration nào.
* **Trạng thái Frontend:** Dự án có 5 trang giao diện React mẫu (`src/routes/*`), toàn bộ đang sử dụng dữ liệu tĩnh (Mock Data/Hardcoded), chưa từng được kết nối đến Database.
* **Tài nguyên tái sử dụng (Core Asset):** File `knowledge_base.json` được tạo từ Phase 4 chứa **162 chunks tri thức chuẩn hóa**, 100% dữ liệu có ID duy nhất (`tea_000001` đến `tea_000162`), sẵn sàng để seed trực tiếp vào Database.

---

## 2. Audit Matrix

| Thành phần | Hiện trạng trong Code | Đánh giá / Giải pháp triển khai Phase 3 |
| :--- | :---: | :--- |
| **Database Engine** | **CHƯA CÓ** | Khởi tạo SQLite DB local (`database/tea_scholar.db`) tương thích chuẩn ANSI SQL với PostgreSQL. |
| **ORM Library** | **ĐÃ CÓ (SQLAlchemy)** | Sử dụng SQLAlchemy 2.0 Declarative Mapping để định nghĩa 8 bảng dữ liệu module. |
| **Migration Tool** | **ĐÃ CÓ (Alembic)** | Cấu hình Alembic Migration framework và tạo kịch bản tạo bảng tự động. |
| **Database Schema** | **CHƯA CÓ** | Thiết kế 7 modules: Users, Documents, Knowledge Chunks, Tea Diseases, Cultivation, Weather, Chat. |
| **Seed Data** | **SẴN SÀNG** | Sử dụng file `knowledge_base.json` (162 chunks) từ Phase 4 để nạp vào DB. |
| **Verification Tests** | **CHƯA CÓ** | Xây dựng kịch bản `verify_database.py` kiểm tra kết nối, Foreign Key và so khớp 162/162 chunks. |

---

## 3. Lựa chọn Công nghệ Database

* **Development & Local Execution:** **SQLite** (`database/tea_scholar.db`) — nhẹ, không yêu cầu cài đặt server rườm rà, sẵn sàng cho việc phát triển backend API ở Phase 5.
* **Production Architecture:** **PostgreSQL** — Toàn bộ Schema được thiết kế sử dụng kiểu dữ liệu tiêu chuẩn (ANSI SQL: `INTEGER`, `VARCHAR`, `TEXT`, `DATETIME`, `BOOLEAN`, `FOREIGN KEY`), giúp dự án dễ dàng chuyển đổi sang PostgreSQL mà không cần sửa đổi định nghĩa ORM Model.

---

## 4. Danh sách các Bảng cần tạo mới (Target Schema)

1. `users`: Quản lý tài khoản người dùng và quản trị viên.
2. `documents`: Quản lý danh mục 3 tài liệu nguồn gốc.
3. `knowledge_chunks`: Quản lý 162 chunks tri thức (liên kết 1:N với `documents`).
4. `tea_diseases`: Quản lý danh mục các loại bệnh sâu hại trên cây chè.
5. `tea_cultivation_topics`: Quản lý danh mục các chủ đề kỹ thuật canh tác chè.
6. `weather_data`: Lưu trữ dữ liệu và thông số thời tiết nông nghiệp.
7. `chat_sessions`: Quản lý các phiên hội thoại chatbot của người dùng.
8. `chat_messages`: Lưu vết câu hỏi - câu trả lời trong từng phiên chat.

---

## 5. Kết luận Audit

Project hiện tại hoàn toàn trống về phía Database backend. Việc triển khai Phase 3 sẽ tạo ra toàn bộ cấu trúc bảng, các mối quan hệ (Relationships), chỉ mục (Indexes), ràng buộc dữ liệu (Constraints), công cụ migration và script seed 162 chunks tri thức từ Phase 4.
