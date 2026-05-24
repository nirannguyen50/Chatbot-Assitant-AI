from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    APP_NAME: str = "Chatbot Platform"
    DEBUG: bool = False

    DATABASE_URL: str = "sqlite:///./chatbot.db"

    SECRET_KEY: str = "change-this-in-production-must-be-at-least-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 ngày

    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Embedding chạy local bằng sentence-transformers (free, ~90MB)
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    CHROMA_PERSIST_DIR: str = "./chroma_db"
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 50 * 1024 * 1024  # 50MB

    # ── Email (SMTP) ─────────────────────────────────
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"


settings = Settings()
