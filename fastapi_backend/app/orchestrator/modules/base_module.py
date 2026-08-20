from __future__ import annotations

from abc import ABC, abstractmethod

from app.orchestrator.schemas.module_response import ModuleResponse
from app.orchestrator.schemas.student_context import StudentContext


class BaseModule(ABC):
    """Abstract interface implemented by future student orchestration modules."""

    name: str

    @abstractmethod
    async def execute(self, context: StudentContext, query: str) -> ModuleResponse:
        """Execute the module for a student context and natural-language query."""
