# Deploy Tea Scholar AI (miễn phí, tự động bằng GitHub Actions)

```
git push lên main
   └─ GitHub Actions
        ├─ test             chạy toàn bộ test backend + RAG (lỗi thì dừng, không deploy)
        ├─ deploy-backend   đẩy backend lên Hugging Face Space → Space tự build Docker
        └─ deploy-frontend  build giao diện → deploy lên Cloudflare Workers
```

| Thành phần | Nơi chạy | Gói miễn phí |
|---|---|---|
| Giao diện (TanStack Start) | Cloudflare Workers | 100.000 request/ngày |
| Backend (FastAPI + embedding bkai + ChromaDB) | Hugging Face Spaces (Docker) | 2 vCPU, 16 GB RAM; ngủ sau 48 giờ không có người dùng |
| Database (tài khoản, lịch sử chat) | Neon Postgres | 1 GB |
| LLM | Groq API (`openai/gpt-oss-120b`) | 200.000 token/ngày ≈ 95 câu hỏi |

Ollama (model chạy trên máy) **không** dùng khi deploy: gói miễn phí không có GPU. Backend trên Space dùng Groq
(`LLM_PROVIDER=groq` đã đặt sẵn trong `Dockerfile`).

## Bước 1. Đưa dự án lên GitHub

```bash
git init
git add .
git commit -m "Tea Scholar AI"
git branch -M main
git remote add origin https://github.com/<tài-khoản>/<tên-repo>.git
git push -u origin main
```

`.env` đã nằm trong `.gitignore` nên API key không bị đẩy lên. Lần push đầu chỉ chạy job `test`; hai job deploy
bị bỏ qua cho đến khi khai báo xong biến ở Bước 5.

## Bước 2. Tạo database Neon

1. Đăng ký tại https://neon.com, tạo project (chọn vùng Singapore cho gần Việt Nam).
2. Mục **Connection string**: chọn driver **psycopg2** / SQLAlchemy, sao chép chuỗi dạng
   `postgresql://user:password@ep-xxx.ap-southeast-1.aws.neon.tech/neondb?sslmode=require`.
   Đây là `DATABASE_URL`. Bảng và dữ liệu mẫu được tạo tự động mỗi khi backend khởi động.

## Bước 3. Tạo token Hugging Face

1. Đăng ký tại https://huggingface.co.
2. **Settings → Access Tokens → Create new token**, loại **Write**. Đây là `HF_TOKEN`.
3. Chọn tên Space, ví dụ `<user-hf>/tea-scholar-api` (`HF_SPACE`). Không cần tạo Space bằng tay: lần deploy đầu tiên tự tạo.
4. Địa chỉ backend (`BACKEND_URL`) sẽ là `https://<user-hf>-tea-scholar-api.hf.space`
   (chữ thường; dấu `_` và `.` trong tên được thay bằng `-`).

## Bước 4. Tạo token Cloudflare

1. Đăng ký tại https://dash.cloudflare.com.
2. **My Profile → API Tokens → Create Token → mẫu "Edit Cloudflare Workers"**. Đây là `CLOUDFLARE_API_TOKEN`.
3. **Account ID** hiện ở trang Workers & Pages (cột bên phải). Đây là `CLOUDFLARE_ACCOUNT_ID`.
4. Lần đầu vào Workers & Pages, Cloudflare yêu cầu chọn tên miền con `<tên>.workers.dev`.
   Địa chỉ giao diện (`FRONTEND_URL`) sẽ là `https://tea-scholar.<tên>.workers.dev`.

## Bước 5. Khai báo trong GitHub

Repo → **Settings → Secrets and variables → Actions**.

**Secrets** (giá trị bị ẩn):

| Tên | Giá trị |
|---|---|
| `HF_TOKEN` | Token Hugging Face (Bước 3) |
| `GROQ_API_KEY` | Key Groq (giống trong `.env`) |
| `DATABASE_URL` | Chuỗi kết nối Neon (Bước 2) |
| `SECRET_KEY` | Chuỗi ngẫu nhiên, tạo bằng `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `CLOUDFLARE_API_TOKEN` | Token Cloudflare (Bước 4) |
| `CLOUDFLARE_ACCOUNT_ID` | Account ID Cloudflare (Bước 4) |
| `GEMINI_API_KEY` | (Không bắt buộc) key Gemini làm dự phòng khi Groq hết hạn mức |

**Variables** (giá trị hiển thị):

| Tên | Ví dụ |
|---|---|
| `HF_SPACE` | `hieuvh/tea-scholar-api` |
| `BACKEND_URL` | `https://hieuvh-tea-scholar-api.hf.space` |
| `FRONTEND_URL` | `https://tea-scholar.hieuvh.workers.dev` |
| `LLM_FALLBACKS` | (Không bắt buộc) `gemini:<tên model Gemini Flash-Lite>`, xem tên model trong Google AI Studio |

Workflow tự chép `GROQ_API_KEY`, `DATABASE_URL`, `SECRET_KEY`, `GEMINI_API_KEY` vào Secrets của Space và đặt
`CORS_ORIGINS = FRONTEND_URL`, nên không cần vào trang Space để khai báo.

## Bước 6. Deploy

Push một commit bất kỳ lên `main`, hoặc vào tab **Actions → Test và deploy → Run workflow**.

- Job `test` mất khoảng 5–8 phút (lần đầu tải model bkai; các lần sau dùng lại bộ nhớ đệm).
- Sau khi `deploy-backend` xong, Space tiếp tục build Docker khoảng 5–10 phút. Theo dõi ở
  `https://huggingface.co/spaces/<HF_SPACE>` (tab Logs).
- Kiểm tra backend: mở `BACKEND_URL/api/v1/health`, kết quả `{"status":"ok", ...}`.
- Mở `FRONTEND_URL` và hỏi thử.

## Giới hạn cần biết

- **Khoảng 95 câu hỏi/ngày** với Groq miễn phí. Thêm `GEMINI_API_KEY` và `LLM_FALLBACKS` để có dự phòng.
- **Space ngủ sau 48 giờ không có người truy cập**; người đầu tiên sau đó chờ khoảng 1–2 phút.
- **Space miễn phí để công khai** thì ai cũng xem được mã backend; key nằm trong Secrets nên không lộ.
- Cloudflare Workers miễn phí giới hạn 10 ms CPU cho mỗi request. Nếu trang báo lỗi vượt giới hạn CPU, cần chuyển
  giao diện sang dạng trang tĩnh.

## Xử lý sự cố

| Hiện tượng | Nguyên nhân thường gặp |
|---|---|
| Job deploy bị bỏ qua (Skipped) | Chưa khai báo Variable `HF_SPACE` hoặc `BACKEND_URL` |
| Giao diện báo lỗi kết nối / CORS | `FRONTEND_URL` không khớp đúng địa chỉ giao diện (kể cả `https://`, không có `/` ở cuối) |
| Space báo `SECRET_KEY is required` | Chưa khai báo Secret `SECRET_KEY` |
| Câu trả lời báo hết hạn mức | Groq đã dùng hết 200.000 token trong ngày; chờ sang ngày hoặc thêm Gemini dự phòng |

## Các file liên quan

- `Dockerfile`, `.dockerignore`, `scripts/deploy/start.sh`: build và khởi động backend trên Space
- `scripts/deploy/push_to_hf_space.py`, `scripts/deploy/space_README.md`: đẩy backend lên Space
- `.github/workflows/deploy.yml`: workflow GitHub Actions
