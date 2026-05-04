import os
from dotenv import load_dotenv

load_dotenv()


def normalize_database_url(url: str | None) -> str:
    if not url:
        return "sqlite:///voiceflow.db"

    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)

    return url


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = normalize_database_url(os.getenv("DATABASE_URL"))
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    PREFERRED_URL_SCHEME = "https"