from __future__ import annotations

from uuid import uuid4

import pytest

from app.models.agentic import ModuleExecution, OrchestratorRun, WorkflowEvent
from app.orchestrator.memory.memory_manager import MemoryManager
from app.orchestrator.modules.base_module import BaseModule
from app.orchestrator.modules.module_registry import ModuleRegistry
from app.orchestrator.observability.run_tracker import COMPLETED, FAILED, RUNNING, RunTracker
from app.orchestrator.observability.workflow_tracker import (
    CONTEXT_LOADED,
    FAILURE,
    INTENT_IDENTIFIED,
    MEMORY_UPDATE_COMPLETED,
    MEMORY_UPDATE_FAILED,
    MEMORY_UPDATE_STARTED,
    MODULE_EXECUTION_COMPLETED,
    MODULE_EXECUTION_STARTED,
    MODULES_SELECTED,
    RESPONSE_COMPOSED,
)
from app.orchestrator.router.module_selector import ACADEMIC_PLANNING
from app.orchestrator.schemas.module_response import ModuleResponse
from app.orchestrator.schemas.student_context import StudentContext
from app.orchestrator.services.student_orchestrator import StudentOrchestrator


class FakeAsyncSession:
    def __init__(self) -> None:
        self.added = []
        self.commit_count = 0
        self.rollback_count = 0

    def add(self, item) -> None:
        self.added.append(item)

    async def commit(self) -> None:
        self.commit_count += 1

    async def rollback(self) -> None:
        self.rollback_count += 1


class FakeContextLoader:
    async def load(self, user_id, plan_id, query):
        return StudentContext(
            user={"id": user_id},
            plan={"plan_id": str(plan_id)},
            program={"name": "Computer Science"},
            university={"name": "Example University"},
        )


class FailingContextLoader:
    async def load(self, user_id, plan_id, query):
        raise RuntimeError("context unavailable")


class PlanningModule(BaseModule):
    name = ACADEMIC_PLANNING

    async def execute(self, context: StudentContext, query: str) -> ModuleResponse:
        return ModuleResponse(module_name=self.name, content="tracked")


class FailingMemoryManager(MemoryManager):
    async def update_memory(self, user_id, plan_id, run_id, query, response):
        raise RuntimeError("memory unavailable")


def build_orchestrator(
    session: FakeAsyncSession,
    *,
    context_loader=None,
    memory_manager=None,
) -> StudentOrchestrator:
    registry = ModuleRegistry()
    registry.register(PlanningModule())
    return StudentOrchestrator(
        db=session,
        context_loader=context_loader or FakeContextLoader(),
        module_registry=registry,
        memory_manager=memory_manager,
    )


@pytest.mark.asyncio
async def test_successful_run_tracking():
    session = FakeAsyncSession()
    plan_id = uuid4()

    response = await build_orchestrator(session).run(
        user_id=1,
        plan_id=plan_id,
        query="What courses should I take next semester?",
    )

    run = next(item for item in session.added if isinstance(item, OrchestratorRun))
    assert run.user_id == 1
    assert run.plan_id == plan_id
    assert run.query == "What courses should I take next semester?"
    assert run.intent == "academic_planning"
    assert run.selected_modules == [ACADEMIC_PLANNING]
    assert run.status == COMPLETED
    assert run.started_at is not None
    assert run.completed_at is not None
    assert response.metadata["status"] == "success"


@pytest.mark.asyncio
async def test_workflow_event_creation():
    session = FakeAsyncSession()

    await build_orchestrator(session).run(
        user_id=1,
        plan_id=uuid4(),
        query="What courses should I take next semester?",
    )

    event_types = [item.event_type for item in session.added if isinstance(item, WorkflowEvent)]
    assert event_types == [
        CONTEXT_LOADED,
        INTENT_IDENTIFIED,
        MODULES_SELECTED,
        MODULE_EXECUTION_STARTED,
        MODULE_EXECUTION_COMPLETED,
        RESPONSE_COMPOSED,
        MEMORY_UPDATE_STARTED,
        MEMORY_UPDATE_COMPLETED,
    ]


@pytest.mark.asyncio
async def test_module_execution_tracking():
    session = FakeAsyncSession()

    await build_orchestrator(session).run(
        user_id=1,
        plan_id=uuid4(),
        query="What courses should I take next semester?",
    )

    execution = next(item for item in session.added if isinstance(item, ModuleExecution))
    assert execution.module_name == ACADEMIC_PLANNING
    assert execution.status == COMPLETED
    assert execution.success is True
    assert execution.started_at is not None
    assert execution.completed_at is not None
    assert execution.duration_ms is not None


@pytest.mark.asyncio
async def test_orchestrator_failure_tracking():
    session = FakeAsyncSession()

    with pytest.raises(RuntimeError, match="context unavailable"):
        await build_orchestrator(session, context_loader=FailingContextLoader()).run(
            user_id=1,
            plan_id=uuid4(),
            query="What courses should I take next semester?",
        )

    run = next(item for item in session.added if isinstance(item, OrchestratorRun))
    events = [item for item in session.added if isinstance(item, WorkflowEvent)]
    assert run.status == FAILED
    assert run.completed_at is not None
    assert "context unavailable" in run.error
    assert events[-1].event_type == FAILURE
    assert events[-1].event_metadata["stage"] == "context_loading"


@pytest.mark.asyncio
async def test_memory_failure_does_not_fail_orchestrator():
    session = FakeAsyncSession()

    response = await build_orchestrator(
        session,
        memory_manager=FailingMemoryManager(session),
    ).run(
        user_id=1,
        plan_id=uuid4(),
        query="I prefer morning classes.",
    )

    events = [item for item in session.added if isinstance(item, WorkflowEvent)]
    assert response.metadata["status"] == "no_modules_selected"
    assert events[-1].event_type == MEMORY_UPDATE_FAILED
    assert events[-1].event_metadata["exception_type"] == "RuntimeError"


@pytest.mark.asyncio
async def test_status_transitions():
    session = FakeAsyncSession()
    tracker = RunTracker(session)
    run = await tracker.create_run(1, uuid4(), "Track this")

    await tracker.mark_running(run)
    assert run.status == RUNNING

    await tracker.complete_run(run)
    assert run.status == COMPLETED
