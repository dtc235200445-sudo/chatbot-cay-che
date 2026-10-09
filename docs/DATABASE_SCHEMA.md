# DATABASE SCHEMA DOCUMENTATION

## 1. Overview & Technology Stack

Dự án **Tea Scholar AI** sử dụng kiến trúc Cơ sở dữ liệu quan hệ được thiết kế theo tiêu chuẩn ANSI SQL:

* **ORM Framework:** **SQLAlchemy 2.0 (Declarative Mapping)**
* **Local Database Engine (Development):** **SQLite** (`database/tea_scholar.db`)
* **Production Compatibility:** **PostgreSQL 14+** (Tương thích 100% về kiểu dữ liệu và ràng buộc)
* **Migration Framework:** **Alembic / SQLAlchemy Metadata Auto-creation**

---

## 2. Entity Relationship Diagram (ERD)

```text
               ┌────────────────┐
               │     users      │
               └───────┬────────┘
                       │ 1
                       │
                       │ N
               ┌───────┴────────┐          ┌───────────────────┐
               │ chat_sessions  ├─────────►│   chat_messages   │
               └────────────────┘ 1      N └───────────────────┘

               ┌────────────────┐
               │   documents    │
               └───────┬────────┘
                       │ 1
                       │
                       │ N
               ┌───────┴────────┐
               │knowledge_chunks│
               └────────────────┘

┌──────────────────┐   ┌──────────────────────────┐   ┌──────────────────┐
│   tea_diseases   │   │  tea_cultivation_topics  │   │   weather_data   │
└──────────────────┘   └──────────────────────────┘   └──────────────────┘
```

---

## 3. Table Definitions & Schemas

### 3.1. `users` (Quản lý Người dùng & Admin)

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY, AUTOINCREMENT | Mã định danh người dùng |
| `username` | `VARCHAR(50)` | UNIQUE, NOT NULL, INDEX | Tên đăng nhập |
| `email` | `VARCHAR(100)` | UNIQUE, NOT NULL, INDEX | Email đăng ký |
| `password_hash` | `VARCHAR(255)` | NOT NULL | Mật khẩu mã hóa (PBKDF2/Bcrypt) |
| `full_name` | `VARCHAR(100)` | NULLABLE | Họ và tên |
| `role` | `VARCHAR(20)` | NOT NULL, DEFAULT `'user'` | Vai trò (`'user'`, `'admin'`) |
| `is_active` | `BOOLEAN` | NOT NULL, DEFAULT `TRUE` | Trạng thái kích hoạt |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian tạo |
| `updated_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian cập nhật |

---

### 3.2. `documents` (Quản lý Tài liệu nguồn)

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY, AUTOINCREMENT | ID tài liệu |
| `document_code` | `VARCHAR(100)` | UNIQUE, NOT NULL, INDEX | Mã tài liệu (`TL1_Tea_Technical_Guideline`, ...) |
| `title` | `VARCHAR(255)` | NOT NULL | Tên tài liệu |
| `source` | `TEXT` | NOT NULL | Trích dẫn nguồn |
| `source_type` | `VARCHAR(50)` | NOT NULL | Loại nguồn (`technical_document`, `dataset_documentation`, ...) |
| `dataset` | `VARCHAR(100)` | NULLABLE | Tên bộ dữ liệu |
| `version` | `VARCHAR(20)` | NULLABLE | Phiên bản tài liệu |
| `language` | `VARCHAR(10)` | NOT NULL, DEFAULT `'vi'` | Ngôn ngữ |
| `region` | `VARCHAR(50)` | NULLABLE | Vùng miền |
| `year` | `INTEGER` | NULLABLE | Năm ban hành |
| `file_name` | `VARCHAR(255)` | NULLABLE | Tên file gốc |
| `description` | `TEXT` | NULLABLE | Mô tả nội dung tài liệu |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian khởi tạo |
| `updated_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian cập nhật |

---

### 3.3. `knowledge_chunks` (Lưu trữ Chunks RAG Knowledge Base)

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY, AUTOINCREMENT | ID bản ghi |
| `chunk_id` | `VARCHAR(50)` | UNIQUE, NOT NULL, INDEX | ID duy nhất (`tea_000001` - `tea_000162`) |
| `document_id` | `INTEGER` | FK (`documents.id`), NOT NULL, INDEX | Mã liên kết tài liệu gốc |
| `title` | `VARCHAR(255)` | NOT NULL | Tiêu đề chunk |
| `content` | `TEXT` | NOT NULL | Nội dung tri thức tự nhiên |
| `source` | `TEXT` | NOT NULL, INDEX | Nguồn tham chiếu |
| `source_type` | `VARCHAR(50)` | NOT NULL | Loại nguồn |
| `category` | `VARCHAR(50)` | NOT NULL, INDEX | Danh mục (`cultivation_technique`, `pest_and_disease`, ...) |
| `topic` | `VARCHAR(255)` | NULLABLE, INDEX | Chủ đề đoạn văn |
| `disease` | `VARCHAR(100)` | NULLABLE, INDEX | Tên bệnh hại (nếu có) |
| `dataset` | `VARCHAR(100)` | NULLABLE | Tên bộ dữ liệu gốc |
| `version` | `VARCHAR(20)` | NULLABLE | Phiên bản |
| `language` | `VARCHAR(10)` | NOT NULL, DEFAULT `'vi'` | Ngôn ngữ |
| `region` | `VARCHAR(50)` | NULLABLE | Vùng |
| `section` | `VARCHAR(255)` | NULLABLE | Mục/Chương trong tài liệu |
| `page` | `INTEGER` | NULLABLE | Trang PDF (nếu có) |
| `year` | `INTEGER` | NULLABLE | Năm ban hành |
| `original_chunk_id` | `VARCHAR(50)` | NULLABLE | ID gốc (`TL1-A00`, `tealeaf_0001`, `laichau_0001`) |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian tạo |
| `updated_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian cập nhật |

---

### 3.4. `tea_diseases` (Danh mục Bệnh hại Cây chè)

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY, AUTOINCREMENT | ID bệnh |
| `name` | `VARCHAR(100)` | UNIQUE, NOT NULL, INDEX | Tên bệnh hại (`Rệp xanh`, `Bọ trĩ`, `Red Spider`, ...) |
| `scientific_name` | `VARCHAR(100)` | NULLABLE | Tên khoa học |
| `symptoms` | `TEXT` | NULLABLE | Triệu chứng nhận biết |
| `causes` | `TEXT` | NULLABLE | Nguyên nhân gây bệnh |
| `prevention` | `TEXT` | NULLABLE | Biện pháp phòng trừ |
| `treatment` | `TEXT` | NULLABLE | Biện pháp đặc trị / Thuốc khuyến cáo |
| `severity` | `VARCHAR(20)` | NULLABLE | Mức độ nguy hiểm (`low`, `medium`, `high`, `critical`) |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian tạo |
| `updated_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian cập nhật |

---

### 3.5. `tea_cultivation_topics` (Chủ đề Kỹ thuật Canh tác)

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY, AUTOINCREMENT | ID chủ đề |
| `topic_name` | `VARCHAR(150)` | UNIQUE, NOT NULL, INDEX | Tên chủ đề |
| `category` | `VARCHAR(50)` | NOT NULL, INDEX | Danh mục kỹ thuật |
| `summary` | `TEXT` | NULLABLE | Tóm tắt kỹ thuật |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian tạo |
| `updated_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian cập nhật |

---

### 3.6. `weather_data` (Dữ liệu Thời tiết Nông nghiệp)

| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY, AUTOINCREMENT | ID bản ghi |
| `region` | `VARCHAR(50)` | NOT NULL, INDEX | Vùng trồng chè (`Phú Thọ`, `Thái Nguyên`, `Lâm Đồng`, ...) |
| `latitude` | `FLOAT` | NULLABLE | Vĩ độ |
| `longitude` | `FLOAT` | NULLABLE | Kinh độ |
| `temperature` | `FLOAT` | NULLABLE | Nhiệt độ (°C) |
| `humidity` | `FLOAT` | NULLABLE | Độ ẩm (%) |
| `rainfall` | `FLOAT` | NULLABLE | Lượng mưa (mm) |
| `wind_speed` | `FLOAT` | NULLABLE | Tốc độ gió (m/s) |
| `weather_condition` | `VARCHAR(50)` | NULLABLE | Trạng thái thời tiết (`Sunny`, `Partly cloudy`, ...) |
| `recorded_at` | `DATETIME` | NULLABLE | Thời điểm đo |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian ghi |

---

### 3.7. `chat_sessions` & `chat_messages` (Phiên và Tin nhắn Chatbot)

#### `chat_sessions`
| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY, AUTOINCREMENT | ID phiên chat |
| `user_id` | `INTEGER` | FK (`users.id`), NULLABLE, INDEX | Mã người dùng |
| `title` | `VARCHAR(255)` | NOT NULL, DEFAULT `'Cuộc trò chuyện mới'` | Tiêu đề phiên chat |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian tạo |
| `updated_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian cập nhật |

#### `chat_messages`
| Column | Data Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | PRIMARY KEY, AUTOINCREMENT | ID tin nhắn |
| `session_id` | `INTEGER` | FK (`chat_sessions.id`), NOT NULL, INDEX | Mã phiên chat |
| `role` | `VARCHAR(20)` | NOT NULL | Vai trò (`user`, `assistant`, `system`) |
| `content` | `TEXT` | NOT NULL | Nội dung tin nhắn |
| `sources_json` | `TEXT` | NULLABLE | Trích dẫn nguồn trích xuất RAG (Chuỗi JSON) |
| `created_at` | `DATETIME` | NOT NULL, DEFAULT `NOW()` | Thời gian tạo |

---

## 4. Indexing & Optimization Strategy

Hệ thống đánh chỉ mục (Index) trên các trường tần suất truy vấn cao:

1. `users`: `email`, `username` -> Tối ưu hóa truy vấn đăng nhập & xác thực.
2. `documents`: `document_code` -> Tối ưu hóa truy vấn tài liệu gốc.
3. `knowledge_chunks`: `chunk_id`, `document_id`, `category`, `disease`, `topic`, `source` -> Tối ưu hóa RAG Context Retrieval và Filter theo danh mục/bệnh hại ở Backend API (Phase 5 & 6).
4. `tea_diseases`: `name` -> Tối ưu hóa tìm kiếm bệnh hại.
5. `weather_data`: `region` -> Tối ưu hóa truy vấn thời tiết theo tỉnh thành.

---

## 5. Seed & Verification Process

1. Khởi chạy `python database/seed.py`:
   * Nạp 3 tài liệu nguồn vào bảng `documents`.
   * Nạp chính xác **162 chunks** từ `data/knowledge_base.json` vào bảng `knowledge_chunks` (gắn Foreign Key liên kết `documents.id`).
   * Trích xuất các bệnh hại chuyên biệt vào bảng `tea_diseases`.
   * Khởi tạo tài khoản `admin` và vị trí thời tiết 4 vùng chè chính.
2. Khởi chạy `python database/verify_database.py`:
   * Kiểm tra kết nối DB.
   * Kiểm tra đầy đủ 8 bảng.
   * Kiểm tra ràng buộc Foreign Key và Unique `chunk_id`.
   * **So khớp 100% (162/162)** nội dung và metadata giữa `data/knowledge_base.json` và bảng `knowledge_chunks`.
