# Backend Tea Scholar AI cho Hugging Face Spaces (Docker, gói CPU Basic miễn phí: 2 vCPU, 16 GB RAM).
# Space chạy container với user uid 1000 và chờ ứng dụng ở cổng 7860.
#
# Khi build: cài PyTorch bản CPU, tải model embedding bkai và tạo ChromaDB từ data/knowledge_base.json,
# nên container khởi động không phải tải gì thêm.
FROM python:3.12-slim

RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    HF_HOME=/home/user/app/.hf_cache \
    PORT=7860 \
    LLM_PROVIDER=groq \
    APP_ENV=production
WORKDIR /home/user/app

# Bản PyTorch CPU nhỏ hơn nhiều so với bản CUDA mặc định trên Linux (Space miễn phí không có GPU)
RUN pip install --no-cache-dir --user torch --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .
# Tạo chỉ mục vector (đồng thời tải model embedding vào HF_HOME)
RUN python -m rag.ingest

EXPOSE 7860
CMD ["sh", "scripts/deploy/start.sh"]
