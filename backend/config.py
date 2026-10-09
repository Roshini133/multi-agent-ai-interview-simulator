"""Central configuration. Every value can be overridden with an environment variable / .env file."""
import logging
import os
import secrets
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _bool(name: str, default: bool) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except ValueError:
        return default


class Config:
    ENV = os.getenv("APP_ENV", "development")
    DEBUG = _bool("FLASK_DEBUG", False)
    TESTING = False

    # SECRET_KEY must be set in production, otherwise a random key is generated per process
    # (tokens are then invalidated on every restart).
    SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
    SECRET_KEY_FROM_ENV = bool(os.getenv("SECRET_KEY"))
    TOKEN_MAX_AGE_SECONDS = _int("TOKEN_MAX_AGE_SECONDS", 60 * 60 * 12)

    # Database (SQLite for dev, PostgreSQL: postgresql+psycopg2://user:pass@host:5432/db)
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", f"sqlite:///{(BASE_DIR / 'data' / 'interview.db').as_posix()}")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000").split(",") if o.strip()]

    # Ollama / LLM
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
    OLLAMA_TIMEOUT = _int("OLLAMA_TIMEOUT", 90)
    OLLAMA_RETRIES = _int("OLLAMA_RETRIES", 2)
    LLM_ENABLED = _bool("LLM_ENABLED", True)

    # Uploads
    MAX_CONTENT_LENGTH = _int("MAX_UPLOAD_MB", 8) * 1024 * 1024
    MAX_RESUME_MB = _int("MAX_RESUME_MB", 5)
    MAX_AUDIO_MB = _int("MAX_AUDIO_MB", 8)
    MAX_FRAME_KB = _int("MAX_FRAME_KB", 600)

    # Interview plan: number of questions asked by each agent
    HR_QUESTIONS = _int("HR_QUESTIONS", 4)
    TECHNICAL_QUESTIONS = _int("TECHNICAL_QUESTIONS", 5)
    MANAGER_QUESTIONS = _int("MANAGER_QUESTIONS", 3)
    MAX_ANSWER_CHARS = _int("MAX_ANSWER_CHARS", 4000)

    # Optional AI components
    EMBEDDINGS_ENABLED = _bool("EMBEDDINGS_ENABLED", True)
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    WHISPER_ENABLED = _bool("WHISPER_ENABLED", False)
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base.en")
    WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")

    # Computer vision
    VISION_ENABLED = _bool("VISION_ENABLED", True)
    MEDIAPIPE_FACE_MODEL = os.getenv("MEDIAPIPE_FACE_MODEL", str(BASE_DIR / "data" / "face_landmarker.task"))
    FACE_ABSENT_SECONDS = _float("FACE_ABSENT_SECONDS", 3.0)
    OFF_SCREEN_SECONDS = _float("OFF_SCREEN_SECONDS", 4.0)
    STORE_VIDEO = False  # frames are analysed in memory and never written to disk

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")


class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    LLM_ENABLED = False
    EMBEDDINGS_ENABLED = False
    WHISPER_ENABLED = False
    SECRET_KEY = "test-secret"
    LOG_LEVEL = "WARNING"
