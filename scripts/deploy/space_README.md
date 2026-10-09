---
title: Tea Scholar API
emoji: 🍵
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
pinned: false
---

# Tea Scholar API

Backend (FastAPI) của chatbot hỏi đáp cây chè Tea Scholar AI: tìm tài liệu bằng embedding tiếng Việt
(bkai vietnamese-bi-encoder) kết hợp BM25, sinh câu trả lời bằng LLM qua Groq.

- Kiểm tra hoạt động: `/api/v1/health`
- Tài liệu API: `/docs`

Space này được cập nhật tự động từ GitHub Actions; không sửa trực tiếp ở đây.
