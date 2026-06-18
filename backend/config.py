import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
APP_DIR = PROJECT_ROOT / "app"

DB_USERS_PATH = str(APP_DIR / "users.db")
DB_LIGHTHOUSE_PATH = str(PROJECT_ROOT / "lighthouse_attributes.db")

JWT_SECRET = os.environ.get("JWT_SECRET", "lighthouse-tools-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24h
