"""
AutoWebAgent - Central Configuration
=====================================
All environment variables and app settings with strong typing.
Supports user-level overrides for API keys.
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field, validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application-wide settings loaded from environment / .env file."""

    # ── Application ──────────────────────────────────────────────
    APP_NAME: str = "AutoWebAgent"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", env="ENVIRONMENT")
    DEBUG: bool = Field(default=True, env="DEBUG")
    SECRET_KEY: str = Field(
        default="super-secret-change-in-production-$(openssl rand -hex 32)",
        env="SECRET_KEY",
    )
    API_PREFIX: str = "/api/v1"
    BACKEND_CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        env="BACKEND_CORS_ORIGINS",
    )

    # ── MongoDB ──────────────────────────────────────────────────
    MONGODB_URI: str = Field(
        default="mongodb://localhost:27017", env="MONGODB_URI"
    )
    MONGODB_DB_NAME: str = Field(
        default="autowebagent", env="MONGODB_DB_NAME"
    )

    # ── Redis ────────────────────────────────────────────────────
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0", env="REDIS_URL"
    )

    # ── JWT Authentication ───────────────────────────────────────
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS"
    )

    # ── DeepSeek LLM (Global / Superadmin Override) ──────────────
    DEEPSEEK_API_KEY: Optional[str] = Field(
        default=None, env="DEEPSEEK_API_KEY"
    )
    DEEPSEEK_MODEL: str = Field(
        default="deepseek-chat", env="DEEPSEEK_MODEL"
    )
    DEEPSEEK_BASE_URL: str = Field(
        default="https://api.deepseek.com/v1", env="DEEPSEEK_BASE_URL"
    )

    # ── Anti-Captcha (Global / Superadmin Override) ──────────────
    ANTICAPTCHA_API_KEY: Optional[str] = Field(
        default=None, env="ANTICAPTCHA_API_KEY"
    )

    # ── CapSolver (Global / Superadmin Override) ─────────────────
    CAPSOLVER_API_KEY: Optional[str] = Field(
        default=None, env="CAPSOLVER_API_KEY"
    )

    # ── Webshare Proxy (Global / Superadmin Override) ────────────
    WEBSHARE_API_KEY: Optional[str] = Field(
        default="lbnnx5zxc7drine5zvxl1tvep8t4od7u2wj6sq7s", env="WEBSHARE_API_KEY"
    )
    WEBSHARE_PROXY_USERNAME: Optional[str] = Field(
        default="hbsbcwnt", env="WEBSHARE_PROXY_USERNAME"
    )
    WEBSHARE_PROXY_PASSWORD: Optional[str] = Field(
        default="gpgyzet0ed8d", env="WEBSHARE_PROXY_PASSWORD"
    )
    WEBSHARE_PROXY_HOST: str = Field(
        default="p.webshare.io", env="WEBSHARE_PROXY_HOST"
    )
    WEBSHARE_PROXY_PORT: int = Field(
        default=80, env="WEBSHARE_PROXY_PORT"
    )

    # ── Browser Automation ──────────────────────────────────────
    BROWSER_HEADLESS: bool = Field(
        default=True, env="BROWSER_HEADLESS"
    )
    BROWSER_TIMEOUT_MS: int = Field(
        default=60000, env="BROWSER_TIMEOUT_MS"
    )
    MAX_CONCURRENT_SESSIONS_PER_USER: int = Field(
        default=5, env="MAX_CONCURRENT_SESSIONS_PER_USER"
    )
    PLAYWRIGHT_BROWSER_PATH: Optional[str] = Field(
        default=None, env="PLAYWRIGHT_BROWSER_PATH"
    )

    # ── Stealth Configuration ────────────────────────────────────
    STEALTH_MODE: str = Field(
        default="ultra", env="STEALTH_MODE",
        description="stealth level: basic | advanced | ultra"
    )
    FINGERPRINT_CONSISTENCY: bool = Field(
        default=True, env="FINGERPRINT_CONSISTENCY"
    )

    # ── Rate Limiting ────────────────────────────────────────────
    RATE_LIMIT_PER_MINUTE: int = Field(
        default=60, env="RATE_LIMIT_PER_MINUTE"
    )

    # ── Logging ──────────────────────────────────────────────────
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(
        default="json", env="LOG_FORMAT",
        description="json | text"
    )

    # ── Encryption ───────────────────────────────────────────────
    ENCRYPTION_KEY: str = Field(
        default="autowebagent-fernet-key-must-be-32-bytes!",
        env="ENCRYPTION_KEY",
    )

    # ── Celery / Task Queue ──────────────────────────────────────
    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1", env="CELERY_BROKER_URL"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND"
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton — avoids re-reading .env every call."""
    return Settings()


settings = get_settings()
