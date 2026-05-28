import os
from dotenv import load_dotenv

if os.getenv("FLASK_ENV", "").lower() != "production" and not os.getenv("RENDER"):
    load_dotenv()


def normalize_database_url(url: str | None) -> str:
    if not url:
        return "sqlite:///smartlecture.db"

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)

    return url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.getenv("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_NAME = "smartlecture_session_v2"
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    MAX_CONTENT_LENGTH = 32 * 1024 * 1024
    SUPPORT_EMAIL = os.getenv("SUPPORT_EMAIL", "support@smartlecture.app")
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    OPENAI_AUDIO_MODEL = os.getenv("OPENAI_AUDIO_MODEL", "gpt-4o-mini-transcribe")
    AI_MAX_INPUT_CHARS = int(os.getenv("AI_MAX_INPUT_CHARS", "20000"))
    AUTO_CREATE_DB = os.getenv("AUTO_CREATE_DB", "true").lower() not in {"0", "false", "no"}


class DevelopmentConfig(Config):
    DEBUG = True
    SECRET_KEY = os.getenv("SECRET_KEY", "development-only-local-secret")
    SESSION_COOKIE_SECURE = False


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.getenv("SECRET_KEY", "smartlecture-production-change-me")
    PREFERRED_URL_SCHEME = "https"
    SESSION_COOKIE_SECURE = True

    @classmethod
    def init_app(cls):
        return None
