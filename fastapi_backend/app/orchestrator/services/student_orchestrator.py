from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agentic import OrchestratorRun
from app.orchestrator.composer.response_composer import ResponseComposer
from app.orchestrator.context.context_loader import ContextLoader
from app.orchestrator.execution.module_executor import ModuleExecutor
from app.orchestrator.graph.graph_builder import build_student_graph
from app.orchestrator.graph.student_graph import StudentGraph
from app.orchestrator.llm.base_provider import BaseLLMProvider
from app.orchestrator.memory.memory_manager import MemoryManager
from app.orchestrator.modules.module_registry import ModuleRegistry
from app.orchestrator.observability.run_tracker import RunTracker
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
    WorkflowTracker,
)
from app.orchestrator.router.intent_router import IntentRouter
from app.orchestrator.router.module_selector import ModuleSelector
from app.orchestrator.schemas.module_response import FinalResponse
from app.orchestrator.schemas.student_context import StudentContext
from app.orchestrator.state.edplan_state import EdPlanState
from app.student.domains.planning.module import (
    MODULE_NAME as ACADEMIC_PLANNING_MODULE_NAME,
)
from app.student.domains.planning.module import (
    AcademicPlanningModule,
)
from app.student.domains.scheduling.module import (
    MODULE_NAME as SCHEDULEPILOT_MODULE_NAME,
)
from app.student.domains.scheduling.module import (
    SchedulePilotModule,
)


class StudentOrchestrator:
    """Application service for running the student orchestration framework."""

    def __init__(
        self,
        db: AsyncSession | None = None,
        context_loader: ContextLoader | None = None,
        intent_router: IntentRouter | None = None,
        module_selector: ModuleSelector | None = None,
        module_registry: ModuleRegistry | None = None,
        module_executor: ModuleExecutor | None = None,
        response_composer: ResponseComposer | None = None,
        graph: StudentGraph | None = None,
        llm_provider: BaseLLMProvider | None = None,
        memory_manager: MemoryManager | None = None,
        run_tracker: RunTracker | None = None,
        workflow_tracker: WorkflowTracker | None = None,
    ) -> None:
        self.module_registry = module_registry or ModuleRegistry()
        if db is not None and not self.module_registry.exists(ACADEMIC_PLANNING_MODULE_NAME):
            self.module_registry.register(AcademicPlanningModule(db=db, llm_provider=llm_provider))
        if db is not None and not self.module_registry.exists(SCHEDULEPILOT_MODULE_NAME):
            self.module_registry.register(SchedulePilotModule(db=db))
        self.context_loader = context_loader or (ContextLoader(db) if db is not None else None)
        self.intent_router = intent_router or IntentRouter()
        self.module_selector = module_selector or ModuleSelector(registry=self.module_registry)
        self.module_executor = module_executor or ModuleExecutor(registry=self.module_registry)
        self.response_composer = response_composer or ResponseComposer()
        self.llm_provider = llm_provider
        self.memory_manager = memory_manager or MemoryManager(db)
        self.run_tracker = run_tracker or RunTracker(db)
        self.workflow_tracker = workflow_tracker or WorkflowTracker(db)
        self._graph_override = graph is not None
        self.graph = graph or build_student_graph(
            context_loader=self.context_loader.load if self.context_loader is not None else None,
            intent_router=self.intent_router.route,
            module_selector=self.module_selector.select,
            module_executor=self.module_executor.execute_selected,
            response_composer=self.response_composer.compose,
        )

    async def run(self, user_id: int, plan_id: UUID, query: str) -> FinalResponse:
        """Run the orchestration stages and persist durable execution trace data."""
        state = EdPlanState(user_id=user_id, plan_id=plan_id, query=query)
        run = await self.run_tracker.create_run(user_id=user_id, plan_id=plan_id, query=query)
        await self.run_tracker.mark_running(run)
        stage_tracker = {"stage": "run_started"}

        try:
            execution_graph = (
                self.graph
                if self._graph_override
                else self._build_observable_graph(run, stage_tracker)
            )
            completed_state = await execution_graph.execute(state)
            if completed_state.final_response is None:
                raise RuntimeError("Student orchestration completed without a final response.")
            await self.run_tracker.complete_run(
                run,
                metadata={
                    "final_response": completed_state.final_response.model_dump(mode="json"),
                    "workflow_event_count": len(completed_state.workflow_events),
                },
            )

            return completed_state.final_response
        except Exception as exc:
            await self.workflow_tracker.record_event(
                getattr(run, "run_id", None),
                FAILURE,
                {
                    "stage": stage_tracker["stage"],
                    "error": str(exc),
                    "exception_type": type(exc).__name__,
                },
            )
            await self.run_tracker.fail_run(run, exc)
            raise

    def _build_observable_graph(
        self,
        run: OrchestratorRun | None,
        stage_tracker: dict[str, str],
    ) -> StudentGraph:
        run_id = getattr(run, "run_id", None)

        async def load_context(user_id: int, plan_id: UUID, query: str) -> StudentContext:
            stage_tracker["stage"] = "context_loading"
            context = (
                await self.context_loader.load(user_id, plan_id, query)
                if self.context_loader is not None
                else StudentContext()
            )
            await self.workflow_tracker.record_event(
                run_id,
                CONTEXT_LOADED,
                _context_metadata_from_context(context),
            )
            return context

        def route_intent(query: str, context: StudentContext | None):
            stage_tracker["stage"] = "intent_routing"
            intent_result = self.intent_router.route(query, context)
            return intent_result

        async def record_intent(query: str, context: StudentContext | None):
            intent_result = route_intent(query, context)
            await self.run_tracker.update_intent(run, intent_result.intent)
            await self.workflow_tracker.record_event(
                run_id,
                INTENT_IDENTIFIED,
                intent_result.model_dump(mode="json"),
            )
            return intent_result

        def select_modules(intent_result):
            stage_tracker["stage"] = "module_selection"
            return self.module_selector.select(intent_result)

        async def record_module_selection(intent_result):
            selection = select_modules(intent_result)
            await self.run_tracker.update_selected_modules(
                run,
                list(selection.selected_modules),
            )
            await self.workflow_tracker.record_event(
                run_id,
                MODULES_SELECTED,
                selection.model_dump(mode="json"),
            )
            return selection

        async def execute_modules(
            selected_modules: list[str],
            context: StudentContext,
            query: str,
        ):
            stage_tracker["stage"] = "module_execution"
            results = {}
            seen_modules: set[str] = set()
            for module_name in selected_modules:
                if module_name in seen_modules:
                    continue
                seen_modules.add(module_name)
                await self.workflow_tracker.record_event(
                    run_id,
                    MODULE_EXECUTION_STARTED,
                    {"module_name": module_name},
                )
                module_execution = await self.run_tracker.record_module_started(run, module_name)
                try:
                    result = await self.module_executor.execute_by_name(module_name, context, query)
                except Exception as exc:
                    await self.run_tracker.record_module_failed(module_execution, exc)
                    raise
                results[module_name] = result
                await self.run_tracker.record_module_completed(module_execution, result)
                await self.workflow_tracker.record_event(
                    run_id,
                    MODULE_EXECUTION_COMPLETED,
                    result.model_dump(mode="json"),
                )
            return results

        def compose_response(context, intent_result, module_results):
            stage_tracker["stage"] = "response_composition"
            return self.response_composer.compose(context, intent_result, module_results)

        async def record_response(context, intent_result, module_results):
            response = compose_response(context, intent_result, module_results)
            await self.workflow_tracker.record_event(
                run_id,
                RESPONSE_COMPOSED,
                response.model_dump(mode="json"),
            )
            return response

        async def update_memory(state: EdPlanState) -> None:
            stage_tracker["stage"] = "memory_update"
            await self.workflow_tracker.record_event(
                run_id,
                MEMORY_UPDATE_STARTED,
                {"has_final_response": state.final_response is not None},
            )
            try:
                if run_id is None:
                    metadata: dict[str, object] = {
                        "memory_saved": False,
                        "reason": "run_id unavailable",
                    }
                else:
                    metadata = await self.memory_manager.update_memory(
                        user_id=state.user_id,
                        plan_id=state.plan_id,
                        run_id=run_id,
                        query=state.query,
                        response=state.final_response,
                    )
                await self.workflow_tracker.record_event(
                    run_id,
                    MEMORY_UPDATE_COMPLETED,
                    metadata,
                )
            except Exception as exc:
                await self.workflow_tracker.record_event(
                    run_id,
                    MEMORY_UPDATE_FAILED,
                    {"error": str(exc), "exception_type": type(exc).__name__},
                )

        return build_student_graph(
            context_loader=load_context,
            intent_router=record_intent,
            module_selector=record_module_selection,
            module_executor=execute_modules,
            response_composer=record_response,
            memory_manager=update_memory,
        )


def _context_metadata_from_context(context: StudentContext) -> dict[str, Any]:
    return {
        "context_loaded": True,
        "has_user": context.user is not None,
        "has_plan": context.plan is not None,
        "has_program": context.program is not None,
        "has_university": context.university is not None,
        "completed_course_count": len(context.completed_courses),
        "preference_count": len(context.preferences),
        "memory_count": len(context.memory),
    }
