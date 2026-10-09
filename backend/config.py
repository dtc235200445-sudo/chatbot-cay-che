import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Nạp biến môi trường từ file .env ở thư mục gốc (nếu có).
# Biến đã đặt sẵn trong môi trường hệ thống được ưu tiên hơn file .env.
load_dotenv(BASE_DIR / ".env", override=False)

logger = logging.getLogger("tea_scholar.config")


def _resolve_secret_key() -> str:
    key = os.getenv("SECRET_KEY", "").strip()
    if key:
        return key
    if os.getenv("APP_ENV", "development").lower() == "production":
        raise RuntimeError("SECRET_KEY is required when APP_ENV=production")
    logger.warning(
        "SECRET_KEY is not set: using a random ephemeral key. "
        "Issued JWT tokens become invalid after every restart."
    )
    return secrets.token_urlsafe(48)


class Settings:
    PROJECT_NAME: str = "Tea Scholar AI Backend"
    API_V1_STR: str = "/api/v1"
    APP_ENV: str = os.getenv("APP_ENV", "development")

    # Environment & Security
    SECRET_KEY: str = _resolve_secret_key()
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))  # 24 hours

    # Database
    BASE_DIR: Path = BASE_DIR
    DB_PATH: Path = BASE_DIR / "database" / "tea_scholar.db"
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")

    # CORS Allowed Origins (có thể ghi đè bằng CORS_ORIGINS="url1,url2")
    CORS_ORIGINS: list[str] = (
        [o.strip() for o in os.environ["CORS_ORIGINS"].split(",") if o.strip()]
        if os.getenv("CORS_ORIGINS")
        else [
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:8001",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:5173",
            "http://127.0.0.1:8001",
            "http://127.0.0.1:8080",
        ]
    )

    # Groq LLM Configs (OpenAI-compatible API)
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_BASE_URL: str = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    # Thử lại tự động khi mất kết nối thoáng qua (openai client dùng thời gian chờ tăng dần giữa các lần thử)
    GROQ_MAX_RETRIES: int = int(os.getenv("GROQ_MAX_RETRIES", "4"))
    GROQ_TIMEOUT_S: float = float(os.getenv("GROQ_TIMEOUT_S", "45"))
    # Model suy luận (gpt-oss) tính cả token "suy nghĩ" vào max_tokens: giới hạn quá thấp làm câu trả lời bị cắt thành rỗng.
    GROQ_MAX_TOKENS: int = int(os.getenv("GROQ_MAX_TOKENS", "1200"))
    # Mức suy luận cho model gpt-oss. Đo trên gpt-oss-20b (24 câu): "low" ít token hơn nhưng câu trả lời dài dòng và kém
    # tuân thủ quy tắc độ dài (85 từ, 4 câu vượt 150 từ) so với "medium" (67 từ, 0 câu vượt 150). Đặt rỗng để không gửi tham số.
    GROQ_REASONING_EFFORT: str = os.getenv("GROQ_REASONING_EFFORT", "medium")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    # Nhà cung cấp LLM chính: "groq" (API, cần GROQ_API_KEY) hoặc "ollama" (model chạy trên máy, không cần key hay mạng).
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "groq").strip().lower()
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
    # Bản qwen2.5:3b có num_ctx 8192 (tạo bằng scripts/ollama/Modelfile.tea-3b): mặc định 4096 của Ollama không đủ cho
    # prompt hệ thống + 6000 ký tự ngữ cảnh + câu trả lời, phần đầu prompt sẽ bị cắt mà không báo lỗi.
    # Chọn 3B vì nằm gọn trong GPU 4 GB; bản 7B phải chạy 58% trên CPU, mất 20–40 giây mỗi câu.
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "tea-qwen2.5:3b")
    # Lần gọi đầu sau khi Ollama giải phóng model (5 phút không dùng) còn mất thời gian nạp lại model.
    OLLAMA_TIMEOUT_S: float = float(os.getenv("OLLAMA_TIMEOUT_S", "240"))
    # Nhà cung cấp dự phòng, thử theo thứ tự khi Groq hết hạn mức hoặc lỗi: "gemini:<model>,cerebras:<model>".
    # Key đọc từ biến môi trường theo llm_service.PROVIDER_REGISTRY (GEMINI_API_KEY, CEREBRAS_API_KEY...)
    LLM_FALLBACKS: str = os.getenv("LLM_FALLBACKS", "")
    MAX_HISTORY_TURNS: int = 5
    MAX_HISTORY_CHARS_PER_TURN: int = 500
    MAX_CONTEXT_CHARS: int = 6000
    MAX_MESSAGE_CHARS: int = 2000
    # Weather Configs (Open-Meteo Integration)
    WEATHER_BASE_URL: str = os.getenv("WEATHER_BASE_URL", "https://api.open-meteo.com/v1/forecast")


settings = Settings()
