"""Application configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://yade:yade_secret@localhost:5432/yade_game"
    SYNC_DATABASE_URL: str = "postgresql://yade:yade_secret@localhost:5432/yade_game"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM
    DASHSCOPE_API_KEY: str = ""
    LLM_MODEL: str = "qwen-max"

    # App
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "change-me-in-production"

    # Chat context
    CHAT_CONTEXT_TTL: int = 3600  # seconds to keep chat context in Redis
    MAX_CHAT_CONTEXT_TURNS: int = 20  # max turns to keep in short-term context

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
