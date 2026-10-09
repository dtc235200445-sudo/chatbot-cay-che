"""
Cấu hình test dùng chung: mỗi lần chạy pytest dùng một DB SQLite tạm đã seed sẵn,
để test không ghi rác vào database/tea_scholar.db thật.

Phải đặt DATABASE_URL TRƯỚC khi bất kỳ module nào import database.connection.
"""
import atexit
import os
import tempfile
from pathlib import Path

_tmp_dir = tempfile.mkdtemp(prefix="tea_scholar_test_")
_db_file = Path(_tmp_dir) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_db_file.as_posix()}"

from database.connection import engine  # noqa: E402
from database.seed import seed_database  # noqa: E402

_KB_PATH = Path(__file__).resolve().parents[2] / "data" / "knowledge_base.json"

seed_database(kb_json_path=str(_KB_PATH))


@atexit.register
def _cleanup() -> None:
    engine.dispose()
    try:
        _db_file.unlink(missing_ok=True)
        Path(_tmp_dir).rmdir()
    except OSError:
        pass  # Windows có thể còn giữ file; thư mục tạm sẽ được hệ điều hành dọn sau


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _llm_provider_groq(monkeypatch):
    """Test LLM giả lập Groq; không để LLM_PROVIDER=ollama trong .env của máy làm đổi chuỗi nhà cung cấp."""
    from backend.config import settings

    monkeypatch.setattr(settings, "LLM_PROVIDER", "groq")
