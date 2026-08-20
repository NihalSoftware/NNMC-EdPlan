from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModuleResponse(BaseModel):
    """Standard response contract for future orchestrator modules."""

    module_name: str = Field(..., min_length=1)
    content: str | None = None
    data: dict[str, Any] = Field(default_factory=dict)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FinalResponse(BaseModel):
    """Final response contract returned by the student orchestrator."""

    message: str
    module_responses: list[ModuleResponse] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
