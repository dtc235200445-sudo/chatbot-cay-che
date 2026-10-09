import os
from pathlib import Path

from dotenv import load_dotenv

# Base Directory of the Project
BASE_DIR = Path(__file__).resolve().parent.parent

# Nạp .env để các script độc lập (seed.py, verify_database.py) dùng chung DATABASE_URL với backend
load_dotenv(BASE_DIR / ".env", override=False)

# Database File Path for Local SQLite
DB_PATH = BASE_DIR / "database" / "tea_scholar.db"

# Database Connection URL (SQLite default, PostgreSQL configurable)
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")
