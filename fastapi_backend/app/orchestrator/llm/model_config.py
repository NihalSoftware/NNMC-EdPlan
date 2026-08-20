from __future__ import annotations

import os

from pydantic import BaseModel, Field, SecretStr, field_validator


class LLMModelConfig(BaseModel):
    """Central model configuration for provider-independent LLM usage."""

    primary_model: str = Field("qwen/qwen3-7b-plus", min_length=1)
    fallback_model: str | None = None
    temperature: float = Field(0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(1024, gt=0)
    timeout: float = Field(30.0, gt=0)
    api_base_url: str = Field("https://openrouter.ai/api/v1", min_length=1)
    api_key: SecretStr | None = Field(default=None, exclude=True)

    @classmethod
    def from_env(cls) -> LLMModelConfig:
        """Build model config from environment variables without requiring app settings."""
        return cls(
            primary_model=os.getenv("OPENROUTER_MODEL", "qwen/qwen3-7b-plus"),
            fallback_model=os.getenv("OPENROUTER_FALLBACK_MODEL") or None,
            temperature=float(os.getenv("OPENROUTER_TEMPERATURE", "0.2")),
            max_tokens=int(os.getenv("OPENROUTER_MAX_TOKENS", "1024")),
            timeout=float(os.getenv("OPENROUTER_TIMEOUT", "30")),
            api_base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=(
                SecretStr(os.environ["OPENROUTER_API_KEY"])
                if os.getenv("OPENROUTER_API_KEY")
                else None
            ),
        )

    @field_validator("primary_model", "fallback_model")
    @classmethod
    def normalize_model_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("model name cannot be blank")
        return normalized

    @field_validator("api_base_url")
    @classmethod
    def normalize_api_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized:
            raise ValueError("api_base_url cannot be blank")
        return normalized
