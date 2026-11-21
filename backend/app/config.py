import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / "backend" / ".env")
DATABASE_PATH = Path(
    os.getenv("GREENTRACK_DATABASE", "").strip()
    or str(ROOT_DIR / "greentrack.sqlite3")
)
APP_ENV = os.getenv("GREENTRACK_ENV", "development").strip().lower()
if APP_ENV not in {"development", "test", "production"}:
    raise ValueError("GREENTRACK_ENV must be development, test, or production.")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip() or None
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
AI_PROVIDER = os.getenv("AI_PROVIDER", "auto").strip().lower()
if AI_PROVIDER not in {"auto", "openai", "gemini"}:
    raise ValueError("AI_PROVIDER must be auto, openai, or gemini.")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip() or None
GEMINI_EMBEDDING_MODEL = os.getenv("GEMINI_EMBEDDING_MODEL", "gemini-embedding-001")
GEMINI_CHAT_MODEL = os.getenv("GEMINI_CHAT_MODEL", "gemini-2.0-flash")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
RAG_SIMILARITY_THRESHOLD = float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.3"))
MAX_UPLOAD_BYTES = 10 * 1024 * 1024
CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "120"))
SESSION_COOKIE_NAME = "greentrack_session"
CSRF_COOKIE_NAME = "greentrack_csrf"
COOKIE_SECURE = os.getenv(
    "GREENTRACK_COOKIE_SECURE", "true" if APP_ENV == "production" else "false"
).strip().lower() == "true"
SESSION_TTL_SECONDS = 60 * 60 * 24 * 7
TRUSTED_HOSTS = [
    host.strip()
    for host in os.getenv("GREENTRACK_TRUSTED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "GREENTRACK_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]
