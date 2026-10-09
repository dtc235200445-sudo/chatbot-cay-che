# PHASE 6 — RAG PIPELINE AUDIT REPORT

## 1. Executive Summary

Trước khi triển khai Phase 6 (Xây dựng RAG Pipeline), chúng tôi đã thực hiện Audit toàn bộ thành phần tri thức, mô hình Vector và môi trường Python nhằm thiết kế một đường ống RAG (Retrieval-Augmented Generation) chuẩn xác, tối ưu hóa cho miền dữ liệu Cây chè Việt Nam.

* **Nguồn dữ liệu đầu vào:** File [knowledge_base.json](file:///e:/CHATBOT%20C%C3%82Y%20CH%C3%88/knowledge_base.json) và Bảng `knowledge_chunks` trong Cơ sở dữ liệu SQLite chứa **162 chunks tri thức tự nhiên** đã được chuẩn hóa ở Phase 4 & Phase 3.
* **Thư viện RAG có sẵn trong môi trường Python:** `chromadb`, `faiss`, `sentence_transformers`, `torch`, `transformers`, `sklearn`, `numpy`.
* **Trạng thái RAG hiện tại:** Chưa có mô hình Vector Embedding, chưa có cơ sở dữ liệu Vector Database và chưa có công cụ Retriever.

---

## 2. Audit Matrix RAG Pipeline Components

| Thành phần RAG | Thư viện & Công nghệ chọn lựa | Vai trò & Kế hoạch triển khai |
| :--- | :---: | :--- |
| **Embedding Engine** | **SentenceTransformers / Scikit-Learn Vectorizer** | Chuyển đổi 162 chunks tri thức dạng văn bản thành các Vector nhúng đa chiều (Multilingual / Vietnamese Support). |
| **Vector Database** | **ChromaDB / Vector Store Persistent** | Lưu trữ lâu dài 162 Chunks Embeddings kèm Metadata đầy đủ tại `database/chroma_db/`. |
| **Similarity Search** | **Cosine Similarity / Dot Product** | Tìm kiếm độ tương đồng không gian vector giữa câu hỏi người dùng và 162 chunks. |
| **Metadata Filtering** | **ChromaDB Filter / Dict Filter** | Hỗ trợ lọc tri thức theo `category`, `disease`, `source`, `region`. |
| **Context Builder** | **Structured Citation Builder** | Đóng gói Top-K chunks được trích xuất thành chuỗi Ngữ cảnh RAG kèm trích dẫn nguồn chuẩn (`[TL1-A01]`, `[laichau_0002]`). |
| **REST API Router** | **FastAPI (`/api/v1/rag/*`)** | Mở rộng 2 RESTful endpoints: `POST /api/v1/rag/query` và `GET /api/v1/rag/search`. |
| **Evaluation Metrics** | **Hit Rate & MRR Calculator** | Đo lường độ chính xác trích xuất tri thức trên bộ câu hỏi thử nghiệm. |

---

## 3. Kiến trúc RAG Pipeline

```text
  User Query ("Cách phòng trừ rệp xanh hại chè?")
                         │
                         ▼
        ┌──────────────────────────────────┐
        │     FastAPI Endpoint             │
        │     POST /api/v1/rag/query       │
        └────────────────┬─────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────┐
        │   Embedding Service              │
        │   (Convert Query -> Vector)      │
        └────────────────┬─────────────────┘
                         │ Query Vector
                         ▼
        ┌──────────────────────────────────┐
        │   Vector Store (ChromaDB)        │
        │   (162 Chunks Indexed)           │
        └────────────────┬─────────────────┘
                         │ Top-K Chunks + Similarity Scores
                         ▼
        ┌──────────────────────────────────┐
        │   Context Builder                │
        │   (Build RAG Context + Sources)   │
        └────────────────┬─────────────────┘
                         │
                         ▼
        ┌──────────────────────────────────┐
        │   RAG Response Payload           │
        │   (Context, Sources, Scores)     │
        └──────────────────────────────────┘
```

---

## 4. Kết luận Audit

Môi trường hiện tại đã đáp ứng đầy đủ 100% điều kiện kỹ thuật để khởi tạo Vector Database và RAG Pipeline. Toàn bộ 162 chunks tri thức sẽ được nạp và đánh chỉ mục vector để phục vụ truy xuất RAG chính xác.
