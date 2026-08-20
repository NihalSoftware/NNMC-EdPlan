from __future__ import annotations

from pydantic import BaseModel, Field


class IntentResult(BaseModel):
    """Intent analysis contract produced by a future routing component."""

    intent: str = Field(..., min_length=1)
    confidence: float = Field(..., ge=0.0, le=1.0)
    target_modules: list[str] = Field(default_factory=list)
    reasoning: str | None = None
