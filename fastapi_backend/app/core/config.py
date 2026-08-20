from functools import lru_cache
from typing import Annotated
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )

    app_name: str = Field("Northern New Mexico College Student Hub API", alias="APP_NAME")
    api_prefix: str = Field("/api", alias="API_V1_PREFIX")
    environment: str = Field("development", alias="ENVIRONMENT")
    debug: bool = Field(False, alias="DEBUG")
    host: str = Field("0.0.0.0", alias="HOST")
    port: int = Field(8000, alias="PORT")

    disable_database: bool = Field(False, alias="DISABLE_DATABASE")
    database_url: str = Field(..., alias="DATABASE_URL")
    db_pool_size: int = Field(5, ge=1, le=50, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(10, ge=0, le=100, alias="DB_MAX_OVERFLOW")
    db_pool_timeout_seconds: int = Field(30, ge=1, le=120, alias="DB_POOL_TIMEOUT_SECONDS")
    outbound_request_timeout_seconds: float = Field(
        15.0, ge=1.0, le=120.0, alias="OUTBOUND_REQUEST_TIMEOUT_SECONDS"
    )

    jwt_secret: str = Field(..., alias="JWT_SECRET")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    jwt_issuer: str = Field("nnmc-edplan-api", alias="JWT_ISSUER")
    jwt_audience: str = Field("nnmc-edplan-web", alias="JWT_AUDIENCE")
    access_token_expire_minutes: int = Field(60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["http://localhost:5173"], alias="CORS_ORIGINS"
    )

    smtp_host: str | None = Field(None, alias="SMTP_HOST")
    smtp_port: int | None = Field(None, alias="SMTP_PORT")
    smtp_username: str | None = Field(None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(None, alias="SMTP_PASSWORD")
    smtp_from_email: str | None = Field(None, alias="SMTP_FROM_EMAIL")
    smtp_from_name: str = Field("NNMC Student Planning Hub", alias="SMTP_FROM_NAME")
    advisor_email_domains: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: ["nnmc.edu"], alias="ADVISOR_EMAIL_DOMAINS"
    )

    twilio_account_sid: str | None = Field(None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(None, alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str | None = Field(None, alias="TWILIO_FROM_NUMBER")

    college_scorecard_api_key: str = Field(..., alias="COLLEGE_SCORECARD_API_KEY")
    college_scorecard_base_url: str = Field(
        "https://api.data.gov/ed/collegescorecard/v1",
        alias="COLLEGE_SCORECARD_BASE_URL",
    )
    openrouter_api_key: SecretStr | None = Field(None, alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field("qwen/qwen3-7b-plus", alias="OPENROUTER_MODEL")
    openrouter_fallback_model: str | None = Field(None, alias="OPENROUTER_FALLBACK_MODEL")
    openrouter_base_url: str = Field(
        "https://openrouter.ai/api/v1",
        alias="OPENROUTER_BASE_URL",
    )
    openrouter_temperature: float = Field(0.2, alias="OPENROUTER_TEMPERATURE")
    openrouter_max_tokens: int = Field(1024, alias="OPENROUTER_MAX_TOKENS")
    openrouter_timeout: float = Field(30.0, alias="OPENROUTER_TIMEOUT")
    default_admin_email: str | None = Field(None, alias="DEFAULT_ADMIN_EMAIL")
    default_admin_password: SecretStr | None = Field(None, alias="DEFAULT_ADMIN_PASSWORD")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            value = [origin.strip() for origin in value.split(",") if origin.strip()]
        return [str(origin).strip().rstrip("/") for origin in value if str(origin).strip()]

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, value: list[str]) -> list[str]:
        for origin in value:
            if origin == "*":
                continue
            parsed = urlparse(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                raise ValueError(f"Invalid CORS origin: {origin}")
        return value

    @field_validator("advisor_email_domains", mode="before")
    @classmethod
    def split_advisor_domains(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            value = value.split(",")
        domains = [str(domain).strip().lower().lstrip("@") for domain in value]
        return [domain for domain in domains if domain]

    @field_validator("jwt_algorithm")
    @classmethod
    def validate_jwt_algorithm(cls, value: str) -> str:
        normalized = value.upper()
        if normalized not in {"HS256", "HS384", "HS512"}:
            raise ValueError("JWT_ALGORITHM must be HS256, HS384, or HS512")
        return normalized

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value: str) -> str:
        if not isinstance(value, str):
            return value

        url = value.strip()

        # Render and other platforms commonly provide "postgres://" URLs.
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]

        # This app uses SQLAlchemy asyncio; ensure an async driver is selected by default.
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

        return url

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        self.environment = self.environment.strip().lower()
        if self.environment not in {"development", "test", "staging", "production"}:
            raise ValueError("ENVIRONMENT must be development, test, staging, or production")
        if self.environment == "production":
            if self.debug:
                raise ValueError("DEBUG must be false in production")
            if not self.cors_origins or "*" in self.cors_origins:
                raise ValueError("Production CORS_ORIGINS must list explicit trusted origins")
            if len(self.jwt_secret) < 32:
                raise ValueError("Production JWT_SECRET must contain at least 32 characters")
        return self


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    # Construct Settings without passing constructor args so BaseSettings reads env vars;
    # static type checkers may incorrectly require all fields as constructor args, so ignore that.
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
