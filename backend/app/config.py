from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from decimal import Decimal
import os


class Settings(BaseSettings):
    APP_NAME: str = "AgentX"
    LOG_LEVEL: str = "INFO"
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/agentx_db"

    # LLM Provider Configuration
    # Options: "mock", "openai", "gemini"
    LLM_PROVIDER: str = "mock"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Embedding Service Configuration
    # Options: "mock", "openai", "gemini"
    EMBEDDING_PROVIDER: str = "mock"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    GEMINI_EMBEDDING_MODEL: str = "models/text-embedding-004"

    # Razorpay Integration Configuration
    RAZORPAY_KEY_ID: str = "rzp_test_dummykey"
    RAZORPAY_KEY_SECRET: str = "dummy_secret"
    RAZORPAY_WEBHOOK_SECRET: str = "dummy_webhook_secret"
    RAZORPAY_CALLBACK_URL: str = "http://localhost:8000/api/payments/callback"

    # Guardrail & Policy Configuration
    HUMAN_APPROVAL_THRESHOLD: Decimal = Decimal("100000.00")
    POLICY_VERSION: str = "v1"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
