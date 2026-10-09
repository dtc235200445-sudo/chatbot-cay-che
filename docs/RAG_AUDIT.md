# Đối chiếu với RAG-pipeline-visualizer

Mục đích: xác định module nào của project tham khảo `RAG-pipeline-visualizer` đáng dùng cho Tea AI. Đây là bản đối chiếu, chưa sao chép mã nguồn nào từ project đó.

## Bản chất của project tham khảo

Ứng dụng Streamlit để thử nghiệm và quan sát từng bước RAG trên **PDF** (loader, chunking, embedding, vector DB, pre/post-retrieval, prompt, generation), xây trên **LangChain** với nhiều thư viện được ghim phiên bản cũ (`numpy==1.26.4`, `chromadb==0.6.3`, `sentence-transformers==3.3.1`, `openai==1.68.2`). Nó là phòng thí nghiệm cấu hình, không phải thư viện để nhúng vào một backend. Gói không có file LICENSE, nên nếu sao chép mã cần xin phép hoặc ghi nguồn tác giả.

## Kết luận từng module

| Module tham khảo | Tea AI hiện có | Quyết định | Lý do |
|---|---|---|---|
| `retrieval/hybrid.py` (RRF/weighted/DBSF) | `rag/retriever.py`: hybrid có trọng số | **Giữ bản của Tea AI** | Bản có trọng số cho MRR 0.956, cao hơn RRF (0.908) trên bộ đánh giá của dự án (xem `RAG_EVALUATION.md`) |
| `embedding/sparse_embedder.py` (BM25: `text.lower().split()`) | `rag/bm25.py` + `rag/text_utils.py` (từ đơn + bigram, bỏ từ dừng, chuẩn hóa Unicode) | **Giữ bản của Tea AI** | Tách từ của mẫu không xử lý tiếng Việt đa âm tiết; bigram giữ được cụm "thối búp", "nhện đỏ" |
| `post_retrieval/cross_encoder_reranker.py` (`bge-reranker-v2-m3`) | Không có | **Chưa dùng** | Hit@3 đã 0.984, Hit@5 là 1.0; dư địa nhỏ so với chi phí model lớn cho mỗi câu hỏi. Xem xét lại nếu bộ đánh giá độc lập cho thấy xếp hạng yếu |
| `pre_retrieval/*` (HyDE, multi-query, step-back) | Ghép câu hỏi nối tiếp bằng luật (`intent_classifier.build_retrieval_query`) | **Chưa dùng** | Mỗi kỹ thuật thêm một lượt gọi LLM cho mỗi câu hỏi; chưa có bằng chứng cần thiết |
| `post_retrieval/mmr_filter.py`, `redundancy_filter.py` | Không có | **Chưa dùng** | Top-3 hiếm khi trùng lặp nghiêm trọng; cân nhắc nếu thấy nguồn trùng nội dung |
| `loader/*`, `chunking/*` | Kho tri thức đã được chia chunk sẵn (`data/knowledge_base.json`) | **Tham khảo cho Phase 4** | Hữu ích nếu bổ sung tài liệu PDF mới hoặc muốn so sánh chiến lược chunking |
| `vector_db/pgvector_store.py` | ChromaDB | **Chỉ đọc tham khảo** | Dùng `langchain_postgres` với bảng riêng `langchain_pg_embedding` và driver `psycopg` v3; khác thiết kế cột `VECTOR(384)` trong `knowledge_chunks` và driver `psycopg2` của Tea AI |
| `prompt/*`, `generation/*` | `backend/services/llm_service.py` (Groq, prompt ràng buộc ngữ cảnh) | **Giữ bản của Tea AI** | Đã tích hợp lịch sử hội thoại, ngữ cảnh thời tiết và xử lý lỗi Groq |
| `app.py`, `ui/*` (Streamlit) | Frontend React | **Không dùng** | Khác công nghệ và mục đích |

## Nếu chuyển sang PostgreSQL + pgvector

- Cần một máy chủ PostgreSQL đã cài extension pgvector.
- Thêm cột `embedding vector(384)` vào `knowledge_chunks` (thiết kế của Tea AI), không dùng bảng LangChain.
- Với 162 chunk, lợi ích chính là gom dữ liệu vào một hệ thống và JOIN với bảng quan hệ, không phải tốc độ. Hybrid hiện tại nạp toàn bộ embedding vào bộ nhớ, phù hợp tới cỡ vài chục nghìn chunk.
- Cần chạy lại `rag/evaluation/run_eval` sau khi chuyển để bảo đảm chất lượng không đổi.

## Thử nghiệm bổ sung: áp dụng vào Tea AI có cải thiện không?

Gói `RAG-pipeline-visualizer-main.zip` bạn gửi lần hai **giống hệt bản đầu** (đã so sánh từng tệp), nên các kết luận ở trên không đổi. Không cài toàn bộ project vào Tea AI vì xung đột phiên bản thư viện (numpy, chromadb, sentence-transformers).

Điều đáng làm hơn hóa ra không nằm trong visualizer: thay **model embedding** bằng model chuyên tiếng Việt (`bkai-foundation-models/vietnamese-bi-encoder`) cho cải thiện lớn nhất, đặc biệt ở khả năng từ chối câu ngoài phạm vi (58% lên 100% trên bộ đánh giá). Chi tiết ở `RAG_EVALUATION.md`, mục 3b. Các kỹ thuật của visualizer (cross-encoder rerank, HyDE, multi-query) chưa thử vì Hit@3 đã đạt 0,986 và mỗi kỹ thuật thêm chi phí; cross-encoder cần tải model mới (khoảng vài trăm MB đến 2 GB).

## Cách dùng project tham khảo hợp lý

Chạy riêng trong môi trường ảo riêng để thử nghiệm chunking trên PDF nguồn và tạo hình minh họa pipeline cho báo cáo. Không cài chung vào môi trường của Tea AI vì xung đột phiên bản thư viện.
