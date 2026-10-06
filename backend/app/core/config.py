from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "OfferReady"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    frontend_url: str = "http://localhost:3000"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    database_url: str = "postgresql+psycopg://offerready:offerready@localhost:5432/offerready"
    auto_create_tables: bool = True
    redis_url: str | None = None

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24 * 7
    cookie_name: str = "or_session"
    cookie_secure: bool = False
    google_client_id: str | None = None
    apple_client_id: str | None = None

    # AI
    ai_provider: str = "alem"  # alem | openai | anthropic | gemini | mock
    ai_model: str = "qwen3-8"
    ai_eval_model: str | None = None
    ai_eval_samples: int = 1  # >1 enables multi-sample median evaluation
    ai_timeout_seconds: float = 90.0
    ai_disable_thinking: bool = True  # Qwen3: append /no_think for structured tasks
    alem_api_key: str | None = None
    alem_base_url: str = "https://llm.alem.ai/v1"
    openai_api_key: str | None = None
    openai_base_url: str = "https://api.openai.com/v1"
    anthropic_api_key: str | None = None
    gemini_api_key: str | None = None
    # USD per 1M tokens (input, output) for cost tracking; override per deployment
    ai_price_input_per_m: float = 0.05
    ai_price_output_per_m: float = 0.10

    # Storage
    storage_backend: Literal["local", "s3"] = "local"
    storage_local_dir: str = "./data/uploads"
    s3_endpoint_url: str | None = None
    s3_bucket: str = "offerready"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    s3_region: str = "us-east-1"
    file_encryption_key: str | None = None  # Fernet key; encrypts uploaded files at rest
    max_upload_mb: int = 5

    # Billing
    payment_provider_default: str = "sandbox"
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None

    # Rate limiting (requests per minute)
    rate_limit_default: int = 120
    rate_limit_ai: int = 30
    rate_limit_auth: int = 10

    admin_email: str | None = None  # user registering with this email becomes admin

    @property
    def is_test(self) -> bool:
        return self.environment == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()
