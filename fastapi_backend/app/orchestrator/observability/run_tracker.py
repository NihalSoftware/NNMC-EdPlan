from __future__ import annotations

from datetime import UTC, datetime
from traceback import format_exception
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agentic import ModuleExecution, OrchestratorRun
from app.orchestrator.execution.module_executor import ModuleExecutionResult

PENDING = "pending"
RUNNING = "running"
COMPLETED = "completed"
FAILED = "failed"


class RunTracker:
    """Persists orchestrator run and module execution tracking."""

    def __init__(self, db: AsyncSession | None) -> None:
        self.db = db

    async def create_run(self, user_id: int, plan_id: UUID, query: str) -> OrchestratorRun | None:
        if self.db is None:
            return None
        run = OrchestratorRun(
            run_id=uuid4(),
            user_id=user_id,
            plan_id=plan_id,
            query=query,
            status=PENDING,
            started_at=_utcnow(),
            selected_modules=[],
            run_metadata={},
        )
        self.db.add(run)
        await self._commit()
        return run

    async def mark_running(self, run: OrchestratorRun | None) -> None:
        if run is None:
            return
        run.status = RUNNING
        await self._commit()

    async def update_intent(self, run: OrchestratorRun | None, intent: str | None) -> None:
        if run is None:
            return
        run.intent = intent
        await self._commit()

    async def update_selected_modules(
        self, run: OrchestratorRun | None, selected_modules: list[str]
    ) -> None:
        if run is None:
            return
        run.selected_modules = list(selected_modules)
        await self._commit()

    async def complete_run(
        self,
        run: OrchestratorRun | None,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if run is None:
            return
        run.status = COMPLETED
        run.completed_at = _utcnow()
        if metadata is not None:
            run.run_metadata = metadata
        await self._commit()

    async def fail_run(self, run: OrchestratorRun | None, exc: BaseException) -> None:
        if run is None:
            return
        run.status = FAILED
        run.completed_at = _utcnow()
        run.error = "".join(format_exception(type(exc), exc, exc.__traceback__))
        await self._commit()

    async def record_module_started(
        self, run: OrchestratorRun | None, module_name: str
    ) -> ModuleExecution | None:
        if self.db is None or run is None:
            return None
        execution = ModuleExecution(
            execution_id=uuid4(),
            run_id=run.run_id,
            module_name=module_name,
            status=RUNNING,
            started_at=_utcnow(),
            execution_metadata={},
        )
        self.db.add(execution)
        await self._commit()
        return execution

    async def record_module_completed(
        self,
        execution: ModuleExecution | None,
        result: ModuleExecutionResult,
    ) -> None:
        if execution is None:
            return
        execution.status = COMPLETED if result.success else FAILED
        execution.success = result.success
        execution.completed_at = _utcnow()
        execution.duration_ms = result.execution_time_ms
        execution.error = result.error
        execution.execution_metadata = {
            "has_response": result.response is not None,
        }
        await self._commit()

    async def record_module_failed(
        self,
        execution: ModuleExecution | None,
        exc: BaseException,
    ) -> None:
        if execution is None:
            return
        execution.status = FAILED
        execution.success = False
        execution.completed_at = _utcnow()
        execution.duration_ms = _duration_ms(execution.started_at, execution.completed_at)
        execution.error = "".join(format_exception(type(exc), exc, exc.__traceback__))
        await self._commit()

    async def _commit(self) -> None:
        if self.db is None:
            return
        try:
            await self.db.commit()
        except Exception:
            await self.db.rollback()
            raise


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _duration_ms(started_at: datetime, completed_at: datetime) -> int:
    return max(0, round((completed_at - started_at).total_seconds() * 1000))
