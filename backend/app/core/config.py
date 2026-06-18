from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "sqlite:///./arogyaai.db"
    SECRET_KEY: str = "dev-only-insecure-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000"]
    APP_NAME: str = "ArogyaAI"
    DEBUG: bool = True

    CACHE_PROVIDER: str = "memory"
    REDIS_URL: str = ""
    REDIS_PREFIX: str = "arogyaai"
    CACHE_TTL_DASHBOARD: int = 300
    CACHE_TTL_ANALYTICS: int = 300
    CACHE_TTL_SEARCH: int = 60
    CACHE_TTL_MEDICINE: int = 3600
    CACHE_TTL_NOTIFICATION: int = 60
    CACHE_TTL_FEATURE_FLAG: int = 300
    CACHE_TTL_DEFAULT: int = 300

    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PROVIDER: str = "memory"
    RATE_LIMIT_DEFAULT: int = 100
    RATE_LIMIT_DEFAULT_WINDOW: int = 60
    RATE_LIMIT_AUTHENTICATED: int = 200
    RATE_LIMIT_AUTHENTICATED_WINDOW: int = 60
    RATE_LIMIT_LOGIN_MAX: int = 5
    RATE_LIMIT_LOGIN_WINDOW: int = 60
    RATE_LIMIT_REGISTER_MAX: int = 3
    RATE_LIMIT_REGISTER_WINDOW: int = 3600
    RATE_LIMIT_BURST_MULTIPLIER: int = 2


settings = Settings()
