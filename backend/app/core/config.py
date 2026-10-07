import os
from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings, loaded from environment / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "OfferReady"
    environment: Literal["development", "test", "production"] = "development"
    api_prefix: str = "/api/v1"
    frontend_url: str | None = None  # public base URL; derived from Vercel env when unset
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    # Accepts DATABASE_URL or POSTGRES_URL (Neon / Vercel Postgres integrations set these).
    database_url: str = Field(
        default="postgresql+psycopg://offerready:offerready@localhost:5432/offerready",
        validation_alias=AliasChoices("DATABASE_URL", "POSTGRES_URL", "database_url"),
    )
    auto_create_tables: bool = True
    redis_url: str | None = None

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60 * 24 * 7
    cookie_name: str = "or_session"
    cookie_secure: bool | None = None  # defaults to True on Vercel / production
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
    # none = keep only extracted CV text (no raw file) — data minimisation, and the default on serverless
    storage_backend: Literal["local", "s3", "none"] | None = None
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
    payments_sandbox: bool | None = None  # test checkout without real money; defaults to on outside production
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None

    # Rate limiting (requests per minute)
    rate_limit_default: int = 120
    rate_limit_ai: int = 30
    rate_limit_auth: int = 10

    admin_email: str | None = None  # user registering with this email becomes admin

    @field_validator("database_url")
    @classmethod
    def _sqlalchemy_driver(cls, v: str) -> str:
        # Hosted Postgres URLs come as postgres:// or postgresql:// — use the psycopg 3 driver.
        for prefix in ("postgres://", "postgresql://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v[len(prefix):]
        return v

    @model_validator(mode="after")
    def _platform_defaults(self) -> "Settings":
        on_vercel = bool(os.environ.get("VERCEL"))
        if self.frontend_url is None:
            host = os.environ.get("VERCEL_PROJECT_PRODUCTION_URL") or os.environ.get("VERCEL_URL")
            self.frontend_url = f"https://{host}" if host else "http://localhost:3000"
        if self.cookie_secure is None:
            self.cookie_secure = on_vercel or self.environment == "production"
        if self.storage_backend is None:
            self.storage_backend = "none" if on_vercel else "local"
        if self.payments_sandbox is None:
            self.payments_sandbox = self.environment != "production"
        return self

    @property
    def is_serverless(self) -> bool:
        return bool(os.environ.get("VERCEL"))

    @property
    def is_test(self) -> bool:
        return self.environment == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()
