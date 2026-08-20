from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from inspect import isawaitable
from typing import Any, TypeVar
from uuid import UUID

from app.orchestrator.execution.module_executor import ModuleExecutionResult
from app.orchestrator.schemas.intent_result import IntentResult
from app.orchestrator.schemas.module_response import FinalResponse
from app.orchestrator.schemas.student_context import StudentContext
from app.orchestrator.schemas.workflow_event import WorkflowEvent
from app.orchestrator.state.edplan_state import EdPlanState

LangGraphStateGraph: Any

try:
    from langgraph.graph import END as LANGGRAPH_END
    from langgraph.graph import START as LANGGRAPH_START
    from langgraph.graph import StateGraph as _LangGraphStateGraph

    LangGraphStateGraph = _LangGraphStateGraph
except ImportError:  # pragma: no cover - exercised only in minimal local envs.
    LANGGRAPH_END = "__end__"
    LANGGRAPH_START = "__start__"
    LangGraphStateGraph = None

START = "START"
CONTEXT_LOADER = "ContextLoader"
INTENT_ROUTER = "IntentRouter"
MODULE_SELECTOR = "ModuleSelector"
MODULE_EXECUTOR = "ModuleExecutor"
RESPONSE_COMPOSER = "ResponseComposer"
MEMORY_MANAGER = "MemoryManager"
END = "END"

StudentGraphNodeHandler = Callable[[EdPlanState], Awaitable[EdPlanState]]
T = TypeVar("T")


@dataclass(frozen=True)
class StudentGraphNode:
    """Named async node in the student orchestration graph."""

    name: str
    handler: StudentGraphNodeHandler


class StudentGraph:
    """LangGraph-backed student orchestration workflow."""

    def __init__(self, nodes: list[StudentGraphNode]) -> None:
        self.nodes = nodes
        self._compiled_graph = self._compile(nodes)

    async def execute(self, state: EdPlanState) -> EdPlanState:
        """Run the compiled LangGraph workflow and return the resulting state."""
        self._record_event(state, START)
        result = await self._compiled_graph.ainvoke(state.model_dump(mode="python"))
        state = self._coerce_state(result)
        self._record_event(state, END)
        return state

    def _compile(self, nodes: list[StudentGraphNode]):
        if LangGraphStateGraph is None:
            return _SequentialStudentGraph(nodes)

        graph = LangGraphStateGraph(EdPlanState)
        for node in nodes:
            graph.add_node(node.name, self._build_langgraph_handler(node))

        if not nodes:
            graph.add_edge(LANGGRAPH_START, LANGGRAPH_END)
        else:
            graph.add_edge(LANGGRAPH_START, nodes[0].name)
            for current_node, next_node in zip(nodes, nodes[1:], strict=False):
                graph.add_edge(current_node.name, next_node.name)
            graph.add_edge(nodes[-1].name, LANGGRAPH_END)

        return graph.compile()

    def _build_langgraph_handler(self, node: StudentGraphNode):
        async def handler(raw_state: EdPlanState | dict) -> dict:
            state = self._coerce_state(raw_state)
            self._record_event(state, node.name)
            updated_state = await node.handler(state)
            return updated_state.model_dump(mode="python")

        return handler

    @staticmethod
    def _coerce_state(raw_state: EdPlanState | dict) -> EdPlanState:
        if isinstance(raw_state, EdPlanState):
            return raw_state
        return EdPlanState.model_validate(raw_state)

    @staticmethod
    def _record_event(state: EdPlanState, event_type: str) -> None:
        state.workflow_events.append(WorkflowEvent(event_type=event_type))


async def load_context_node(state: EdPlanState) -> EdPlanState:
    """Placeholder context node with no database access."""
    if state.student_context is None:
        state.student_context = StudentContext()
    return state


def build_context_loader_node(
    loader: Callable[[int, UUID, str], Awaitable[StudentContext]],
) -> StudentGraphNodeHandler:
    """Build a ContextLoader graph node bound to a loader callable."""

    async def context_loader_node(state: EdPlanState) -> EdPlanState:
        state.student_context = await loader(state.user_id, state.plan_id, state.query)
        return state

    return context_loader_node


async def route_intent_node(state: EdPlanState) -> EdPlanState:
    """Placeholder intent node with no LLM or routing implementation."""
    if state.intent_result is None:
        state.intent_result = IntentResult(
            intent="unclassified",
            confidence=0.0,
            target_modules=[],
            reasoning="Placeholder intent result; routing is not implemented.",
        )
    state.selected_modules = list(state.intent_result.target_modules)
    return state


def build_intent_router_node(
    router: Callable[[str, StudentContext | None], IntentResult | Awaitable[IntentResult]],
) -> StudentGraphNodeHandler:
    """Build an IntentRouter graph node bound to a router callable."""

    async def intent_router_node(state: EdPlanState) -> EdPlanState:
        state.intent_result = await _maybe_await(router(state.query, state.student_context))
        return state

    return intent_router_node


async def select_modules_node(state: EdPlanState) -> EdPlanState:
    """Placeholder module selector that mirrors routed target modules."""
    if state.intent_result is not None:
        state.selected_modules = list(state.intent_result.target_modules)
    return state


def build_module_selector_node(
    selector: Callable[[IntentResult], object | Awaitable[object]],
) -> StudentGraphNodeHandler:
    """Build a ModuleSelector graph node bound to a selector callable."""

    async def module_selector_node(state: EdPlanState) -> EdPlanState:
        if state.intent_result is None:
            state.selected_modules = []
            return state
        selection = await _maybe_await(selector(state.intent_result))
        selected_modules = getattr(selection, "selected_modules", [])
        state.selected_modules = list(selected_modules)
        if hasattr(selection, "model_dump"):
            state.metadata["module_selection"] = selection.model_dump(mode="json")
        return state

    return module_selector_node


def build_module_executor_node(
    executor: Callable[
        [list[str], StudentContext, str], Awaitable[dict[str, ModuleExecutionResult]]
    ],
) -> StudentGraphNodeHandler:
    """Build a ModuleExecutor graph node bound to an executor callable."""

    async def module_executor_node(state: EdPlanState) -> EdPlanState:
        context = state.student_context or StudentContext()
        state.module_results = await executor(state.selected_modules, context, state.query)
        return state

    return module_executor_node


async def execute_modules_node(state: EdPlanState) -> EdPlanState:
    """Placeholder module execution node; no modules are executed."""
    return state


def build_response_composer_node(
    composer: Callable[
        [StudentContext | None, IntentResult | None, dict[str, ModuleExecutionResult]],
        FinalResponse | Awaitable[FinalResponse],
    ],
) -> StudentGraphNodeHandler:
    """Build a ResponseComposer graph node bound to a composer callable."""

    async def response_composer_node(state: EdPlanState) -> EdPlanState:
        state.final_response = await _maybe_await(
            composer(
                state.student_context,
                state.intent_result,
                state.module_results,
            )
        )
        return state

    return response_composer_node


async def compose_response_node(state: EdPlanState) -> EdPlanState:
    """Placeholder response composer with no business-specific response logic."""
    if state.final_response is None:
        state.final_response = FinalResponse(
            message="Student orchestrator foundation executed successfully.",
            module_responses=[
                result.response
                for result in state.module_results.values()
                if result.success and result.response is not None
            ],
        )
    return state


async def update_memory_node(state: EdPlanState) -> EdPlanState:
    """Placeholder memory node with no persistence side effects."""
    return state


def build_memory_manager_node(
    memory_manager: Callable[[EdPlanState], None | Awaitable[None]],
) -> StudentGraphNodeHandler:
    """Build a MemoryManager graph node bound to a memory callable."""

    async def memory_manager_node(state: EdPlanState) -> EdPlanState:
        await _maybe_await(memory_manager(state))
        return state

    return memory_manager_node


async def _maybe_await(value: T | Awaitable[T]) -> T:
    if isawaitable(value):
        return await value
    return value


class _SequentialStudentGraph:
    """Small compatibility runner used when LangGraph is unavailable locally."""

    def __init__(self, nodes: list[StudentGraphNode]) -> None:
        self.nodes = nodes

    async def ainvoke(self, raw_state: EdPlanState | dict) -> dict:
        state = StudentGraph._coerce_state(raw_state)
        for node in self.nodes:
            StudentGraph._record_event(state, node.name)
            state = await node.handler(state)
        return state.model_dump(mode="python")
