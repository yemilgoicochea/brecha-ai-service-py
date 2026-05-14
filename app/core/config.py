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

    # GCP Pub/Sub settings (NEW)
    GCP_PROJECT_ID: str = ""
    PUBSUB_TOPIC_ID: str = "brecha-classification-topic"

    # Supabase settings (NEW)
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""

    # JWT/Auth settings (NEW)
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 24

    # Gemini API settings are handled by the worker service, not this API

    class Config:
        """Pydantic configuration."""

        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


# Create settings instance
settings = Settings()
