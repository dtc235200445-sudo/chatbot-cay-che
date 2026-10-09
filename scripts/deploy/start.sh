#!/bin/sh
# Khởi động backend trong container (Hugging Face Space).
set -e

# Tạo bảng và nạp dữ liệu mẫu vào DATABASE_URL (Neon Postgres). Chạy lại nhiều lần vẫn an toàn:
# seed bỏ qua bản ghi đã có. Không có DATABASE_URL thì dùng SQLite trong container (mất khi Space khởi động lại).
python -m database.seed

exec uvicorn backend.main:app --host 0.0.0.0 --port "${PORT:-7860}"
