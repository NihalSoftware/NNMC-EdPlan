from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

LLMRole = Literal["system", "user", "assistant", "tool"]


class LLMMessage(BaseModel):
    """Provider-neutral chat message contract."""

    role: LLMRole
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMUsage(BaseModel):
    """Token usage metadata compatible with common provider responses."""

    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None


class LLMToolCall(BaseModel):
    """Provider-neutral tool call requested by a chat model."""

    id: str | None = None
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class LLMRequest(BaseModel):
    """Provider-neutral request contract for future LLM calls."""

    messages: list[LLMMessage]
    model: str | None = None
    system_prompt: str | None = None
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(default=None, gt=0)
    tools: list[dict[str, Any]] = Field(default_factory=list)
    tool_choice: str | dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class LLMResponse(BaseModel):
    """Provider-neutral response contract for future LLM calls."""

    model: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    usage: LLMUsage | None = None
    finish_reason: str | None = None
    tool_calls: list[LLMToolCall] = Field(default_factory=list)
    raw_response: dict[str, Any] | None = None


class LLMHealthCheck(BaseModel):
    """Provider health check result without requiring network access."""

    provider: str
    ok: bool
    message: str
    metadata: dict[str, Any] = Field(default_factory=dict)
