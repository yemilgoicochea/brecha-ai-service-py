"""Application configuration."""

import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""

    # App settings
    APP_NAME: str = "Brecha AI Service"
    ENVIRONMENT: str = "development"
    PORT: int = 8080
    LOG_LEVEL: str = "INFO"

    # CORS settings
    ALLOWED_ORIGINS: str = "*"

    # Gemini API settings
    GEMINI_API_KEY: str
    GEMINI_MODEL_NAME: str
    GEMINI_MAX_RETRIES: int = 3
    GEMINI_RETRY_DELAY: int = 2

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Create settings instance
settings = Settings()
