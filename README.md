# Tea Scholar AI

Trợ lý tri thức và hỏi đáp về cây chè Việt Nam. Hệ thống kết hợp **RAG** (truy xuất từ cơ sở tri thức 162 đoạn kỹ thuật chè), **dữ liệu thời tiết thời gian thực** (Open-Meteo) và mô hình ngôn ngữ **Groq (Llama 3.3 70B)** để trả lời có trích dẫn nguồn.

## Kiến trúc

```text
Frontend (TanStack Start, React 19)
        │  REST + JWT
        ▼
Backend FastAPI ── routers → services
        │                     │
        │                     ├── Assistant Orchestrator: phân loại ý định
        │                     │     KNOWLEDGE / WEATHER / HYBRID / GENERAL
        │                     ├── RAG hybrid: embedding + BM25 (top-3, có cổng từ chối)
        │                     ├── Weather: Open-Meteo
        │                     └── LLM: Groq (OpenAI-compatible)
        ▼
SQLite (dev) / PostgreSQL (triển khai) qua SQLAlchemy 2.0
```

| Thư mục | Nội dung |
|---|---|
| `backend/` | FastAPI: routers, services (điều phối trợ lý, phân loại ý định, thời tiết, LLM), schemas, đánh giá câu trả lời, tests |
| `rag/` | RAG hybrid: embedding, BM25, vector store (ChromaDB), retriever, ingest, đánh giá truy xuất (`rag/evaluation/`) |
| `database/` | Models SQLAlchemy, seed, kiểm tra dữ liệu |
| `frontend/` | Giao diện web (`src/routes`, `components/{layout,common,ai-elements,ui}`, `lib`, `context`, `types`) |
| `data/` | `knowledge_base.json` (171 chunk), `raw/` (dữ liệu gốc), `external/` (nguồn ngoài có giấy phép), `tea_regions.json` |
| `scripts/` | Xây dựng và kiểm tra cơ sở tri thức (`build_knowledge_base.py`, `validate_knowledge_base.py`, `build_external_sources.py`) |
| `docs/` | Tài liệu yêu cầu, kiến trúc, đánh giá, nguồn dữ liệu, báo cáo từng phase |

## Yêu cầu

- Python 3.12
- Node.js 20+ (hoặc Bun) cho frontend
- Khóa API Groq: https://console.groq.com

## Chạy backend

```bash
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env              # sau đó điền GROQ_API_KEY và SECRET_KEY

python database/seed.py           # tạo bảng và nạp 162 chunk
python -m rag.ingest              # tạo chỉ mục vector (lần đầu tự tải model embedding tiếng Việt bkai, khoảng 773 MB)

python -m backend.main            # http://127.0.0.1:8001  (tài liệu API: /docs)
```

## Chạy frontend

```bash
cd frontend
npm install                       # hoặc: bun install
npm run dev                       # http://localhost:8080
```

Địa chỉ backend cấu hình bằng `VITE_API_BASE_URL` (mặc định `http://localhost:8001`; cổng 8000 dành cho dự án MediSage).

## Cơ sở dữ liệu

Mặc định dùng **SQLite** (`database/tea_scholar.db`), không cần cài thêm. Có thể trỏ sang PostgreSQL có sẵn bằng biến `DATABASE_URL` trong `.env` (xem `.env.example`), rồi chạy lại `python database/seed.py` (đã kiểm tra seed, đăng ký, đăng nhập, chat và lịch sử trên PostgreSQL 10/2026). Vector embedding luôn nằm trong ChromaDB (`database/chroma_db/`).

## Kiểm thử

```bash
python -m pytest backend/tests -q     # dùng DB SQLite tạm, không ảnh hưởng dữ liệu thật
python -m pytest rag/tests -q         # cần đã chạy python -m rag.ingest
python -m rag.evaluation.run_eval     # đo chất lượng truy xuất RAG
```

Frontend: `npx tsc --noEmit`, `npx eslint src`, `npm run build` (trong thư mục frontend).

## Biến môi trường

Xem `.env.example`. Khi `APP_ENV=production`, `SECRET_KEY` là bắt buộc.

## Deploy

Deploy miễn phí và tự động bằng GitHub Actions: giao diện lên Cloudflare Workers, backend lên Hugging Face Spaces (Docker),
database Neon Postgres, LLM qua Groq. Mỗi lần push lên `main`, workflow chạy test rồi mới deploy.
Hướng dẫn từng bước: [docs/DEPLOY.md](docs/DEPLOY.md).

## Tài liệu

- [Mục lục tài liệu](docs/README.md)
- [Hướng dẫn deploy](docs/DEPLOY.md)
- [Phase 0 — Đề tài và phạm vi](docs/00_PROJECT_SCOPE.md)
- [Phase 1 — Phân tích yêu cầu](docs/01_REQUIREMENTS.md)
- [Phase 2 — Kiến trúc](docs/02_ARCHITECTURE.md)
- [Lược đồ cơ sở dữ liệu](docs/DATABASE_SCHEMA.md)
- [Nguồn dữ liệu và giấy phép](docs/DATA_SOURCES.md)
- [Đánh giá chất lượng câu trả lời của LLM](docs/ANSWER_EVALUATION.md)
- [Hướng nghiên cứu đề xuất](docs/RESEARCH_DIRECTIONS.md)
- [Thiết kế và đánh giá RAG](docs/RAG_EVALUATION.md) (kết quả đo: [RAG_EVAL_RESULTS.md](docs/RAG_EVAL_RESULTS.md))
- [Đối chiếu với RAG-pipeline-visualizer](docs/RAG_AUDIT.md)
- [Báo cáo từng phase](docs/reports/)
