from __future__ import annotations

from uuid import uuid4

import pytest

from app.orchestrator.llm import (
    BaseLLMProvider,
    LLMHealthCheck,
    LLMRequest,
    LLMResponse,
    LLMToolCall,
)
from app.orchestrator.modules.module_registry import ModuleRegistry
from app.orchestrator.router.intent_router import IntentRouter
from app.orchestrator.router.module_selector import ACADEMIC_PLANNING, ModuleSelector
from app.orchestrator.schemas.student_context import StudentContext
from app.orchestrator.services.student_orchestrator import StudentOrchestrator
from app.student.domains.planning.module import AcademicPlanningModule
from app.student.domains.planning.schemas.normalized_plan import PlanCourseCreateRequest
from app.student.domains.planning.tools.courses import AddCourseTool


class _PlanningService:
    def __init__(self) -> None:
        self.calls: list[tuple] = []

    async def add_plan_course(self, db, plan_id, payload):
        self.calls.append(("add_plan_course", db, plan_id, payload))
        return {"plan_id": plan_id, "course_id": payload.course_id, "status": payload.status}


class _FakeAdvisorProvider(BaseLLMProvider):
    provider_name = "fake-qwen"

    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = responses
        self.requests: list[LLMRequest] = []

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        return self.responses.pop(0)

    async def generate_structured(self, request, response_model):
        raise NotImplementedError

    async def health_check(self) -> LLMHealthCheck:
        return LLMHealthCheck(provider=self.provider_name, ok=True, message="ok")


class _RecordingTool:
    def __init__(self, name: str, result: dict | None = None) -> None:
        self.name = name
        self.description = f"{name} test tool"
        self.result = result or {"tool": name, "ok": True}
        self.calls: list[tuple] = []

    async def execute(self, db, *args):
        self.calls.append((db, *args))
        return self.result


class _ContextLoader:
    async def load(self, user_id, plan_id, query):
        return StudentContext(
            user={"id": user_id},
            plan={"plan_id": str(plan_id)},
            program={"program_id": "program-1", "name": "Computer Science"},
            university={"university_id": "university-1", "name": "Reference University"},
        )


def _tool_call(name: str, arguments: dict | None = None) -> LLMToolCall:
    return LLMToolCall(name=name, arguments=arguments or {})


def _provider(*responses: LLMResponse) -> _FakeAdvisorProvider:
    return _FakeAdvisorProvider(list(responses))


def _tool_response(*tool_calls: LLMToolCall) -> LLMResponse:
    return LLMResponse(model="qwen/qwen3-7b-plus", content="", tool_calls=list(tool_calls))


def _final(content: str) -> LLMResponse:
    return LLMResponse(model="qwen/qwen3-7b-plus", content=content)


def _context(plan_id: str = "plan-1") -> StudentContext:
    return StudentContext(
        user={"id": 1},
        plan={"plan_id": plan_id},
        program={"program_id": "program-1", "name": "Computer Science"},
        university={"university_id": "university-1", "name": "Reference University"},
        completed_courses=[{"code": "CS151"}, {"code": "CS152L"}, {"code": "MATH162"}],
    )


def test_intent_router_selects_academic_planning_for_supported_plan_intents():
    router = IntentRouter()
    selector = ModuleSelector()

    intent_result = router.route("Please add course CS101 to my academic plan")
    selection = selector.select(intent_result)

    assert intent_result.intent == "academic_planning"
    assert intent_result.target_modules == [ACADEMIC_PLANNING]
    assert selection.selected_modules == [ACADEMIC_PLANNING]


@pytest.mark.asyncio
async def test_orchestrator_executes_academic_planning_add_course_tool_end_to_end():
    db = object()
    service = _PlanningService()
    course_id = str(uuid4())
    advisor = _provider(
        _tool_response(_tool_call("add_course", {"payload": {"course_id": course_id}})),
        _final("I added the course and confirmed the plan update."),
    )
    registry = ModuleRegistry()
    registry.register(
        AcademicPlanningModule(db=db, tools=[AddCourseTool(service)], llm_provider=advisor)
    )
    plan_id = uuid4()
    orchestrator = StudentOrchestrator(
        context_loader=_ContextLoader(),
        intent_router=IntentRouter(),
        module_registry=registry,
    )

    response = await orchestrator.run(
        user_id=1,
        plan_id=plan_id,
        query="Add course CS151 to my plan.",
    )

    assert response.message == "success"
    assert response.metadata["intent"]["target_modules"] == [ACADEMIC_PLANNING]
    assert response.module_responses[0].module_name == ACADEMIC_PLANNING
    assert response.module_responses[0].metadata["tool_invoked"] == "add_course"
    assert (
        response.module_responses[0].content == "I added the course and confirmed the plan update."
    )
    assert response.module_responses[0].data["observations"][0]["result"] == {
        "plan_id": str(plan_id),
        "course_id": course_id,
        "status": "Planned",
    }
    assert len(service.calls) == 1
    assert service.calls[0][:3] == ("add_plan_course", db, str(plan_id))
    assert isinstance(service.calls[0][3], PlanCourseCreateRequest)
    assert advisor.requests[0].tools
    assert [tool["function"]["name"] for tool in advisor.requests[0].tools] == [
        "create_plan",
        "update_plan",
        "delete_plan",
        "get_plan",
        "add_course",
        "remove_course",
        "move_course",
        "validate_plan",
        "audit_plan",
        "get_remaining_courses",
        "get_course_details",
        "get_prerequisites",
        "get_corequisites",
        "get_program_requirements",
        "get_available_terms",
    ]
    first_prompt = advisor.requests[0].messages[0].content
    assert "compact planning summary" in first_prompt
    assert response.module_responses[0].data["planning_summary"]["completed_courses"] == 0


@pytest.mark.asyncio
async def test_academic_planning_advisor_runs_validation_tool_sequence():
    db = object()
    validate_tool = _RecordingTool("validate_plan", {"is_valid": False})
    audit_tool = _RecordingTool("audit_plan", {"missing": ["CS272"]})
    module = AcademicPlanningModule(
        db=db,
        tools=[validate_tool, audit_tool],
        llm_provider=_provider(
            _tool_response(_tool_call("validate_plan"), _tool_call("audit_plan")),
            _final("Your plan has prerequisite issues and is missing CS272."),
        ),
    )

    response = await module.execute(_context(), "Validate my plan and check graduation blockers.")

    assert response.content == "Your plan has prerequisite issues and is missing CS272."
    assert response.metadata["tools_invoked"] == ["validate_plan", "audit_plan"]
    assert response.data["tool_call_count"] == 2


@pytest.mark.asyncio
async def test_academic_planning_advisor_uses_remaining_courses_for_graduation_readiness():
    remaining_tool = _RecordingTool(
        "get_remaining_courses",
        {"remaining_courses": [{"course_code": "STAT401"}]},
    )
    module = AcademicPlanningModule(
        db=object(),
        tools=[remaining_tool],
        llm_provider=_provider(
            _tool_response(_tool_call("get_remaining_courses")),
            _final("You are close to graduation, but STAT401 remains."),
        ),
    )

    response = await module.execute(_context(), "What courses are left before I graduate?")

    assert response.metadata["tools_invoked"] == ["get_remaining_courses"]
    assert "STAT401" in response.content


@pytest.mark.asyncio
async def test_academic_planning_advisor_compares_multi_semester_plan_options():
    get_plan = _RecordingTool("get_plan", {"courses": ["CS272", "CS321", "STAT401", "CS404"]})
    audit = _RecordingTool("audit_plan", {"remaining_requirements": ["CS272", "CS321"]})
    validate = _RecordingTool("validate_plan", {"is_valid": True})
    module = AcademicPlanningModule(
        db=object(),
        tools=[get_plan, audit, validate],
        llm_provider=_provider(
            _tool_response(
                _tool_call("get_plan"),
                _tool_call("audit_plan"),
                _tool_call("validate_plan", {"payload": {"mode": "draft"}}),
            ),
            _final(
                "Ranked recommendation: Balanced Plan. Aggressive Plan finishes in two "
                "semesters, Balanced Plan spreads CS321 and CS404, Low-Risk Plan uses "
                "lighter credit loads."
            ),
        ),
    )

    response = await module.execute(
        _context(),
        "Can I finish CS272, CS321, STAT401, and CS404 in two semesters?",
    )

    assert response.metadata["tools_invoked"] == ["get_plan", "audit_plan", "validate_plan"]
    assert "Aggressive Plan" in response.content
    assert "Balanced Plan" in response.content
    assert "Low-Risk Plan" in response.content


@pytest.mark.asyncio
async def test_academic_planning_advisor_can_iterate_for_graduation_acceleration():
    get_plan = _RecordingTool("get_plan")
    audit = _RecordingTool("audit_plan")
    validate = _RecordingTool("validate_plan")
    module = AcademicPlanningModule(
        db=object(),
        tools=[get_plan, audit, validate],
        llm_provider=_provider(
            _tool_response(_tool_call("audit_plan")),
            _tool_response(_tool_call("get_plan"), _tool_call("validate_plan")),
            _tool_response(_tool_call("audit_plan")),
            _final("Acceleration is possible only with the aggressive option; balanced is safer."),
        ),
    )

    response = await module.execute(_context(), "Can I graduate next year if I overload?")

    assert response.metadata["tools_invoked"] == [
        "audit_plan",
        "get_plan",
        "validate_plan",
        "audit_plan",
    ]
    assert "Acceleration is possible" in response.content


@pytest.mark.asyncio
async def test_academic_planning_advisor_asks_for_missing_information_without_tools():
    module = AcademicPlanningModule(
        db=object(),
        tools=[],
        llm_provider=_provider(
            _final(
                "I need your program, completed courses, and current plan before I can "
                "recommend a faster graduation path."
            ),
        ),
    )

    response = await module.execute(StudentContext(), "Help me graduate faster.")

    assert response.metadata["tools_invoked"] == []
    assert "I need your program" in response.content


@pytest.mark.asyncio
async def test_academic_planning_advisor_stops_pathological_same_tool_loop():
    audit = _RecordingTool("audit_plan")
    module = AcademicPlanningModule(
        db=object(),
        tools=[audit],
        max_same_tool_calls=2,
        llm_provider=_provider(
            _tool_response(_tool_call("audit_plan")),
            _tool_response(_tool_call("audit_plan")),
            _tool_response(_tool_call("audit_plan")),
            _final("I have enough audit information to answer without more tool calls."),
        ),
    )

    response = await module.execute(_context(), "Keep checking my graduation audit.")

    assert response.metadata["tools_invoked"] == ["audit_plan", "audit_plan"]
    assert response.metadata["tool_budget"]["stop_reason"] == "tool_budget_exhausted"
    assert "enough audit information" in response.content
