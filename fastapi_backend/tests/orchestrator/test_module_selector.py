from __future__ import annotations

from app.orchestrator.modules.base_module import BaseModule
from app.orchestrator.modules.example_module import EXAMPLE_MODULE
from app.orchestrator.modules.module_registry import ModuleRegistry
from app.orchestrator.router.module_selector import ACADEMIC_PLANNING, CAREER, ModuleSelector
from app.orchestrator.schemas.intent_result import IntentResult
from app.orchestrator.schemas.module_response import ModuleResponse
from app.orchestrator.schemas.student_context import StudentContext


class FakeModule(BaseModule):
    def __init__(self, name: str) -> None:
        self.name = name

    async def execute(self, context: StudentContext, query: str) -> ModuleResponse:
        return ModuleResponse(module_name=self.name)


def test_module_selector_supports_single_module_routing():
    result = ModuleSelector().select(
        IntentResult(
            intent="academic_planning",
            confidence=0.8,
            target_modules=[ACADEMIC_PLANNING],
        )
    )

    assert result.selected_modules == [ACADEMIC_PLANNING]
    assert result.invalid_modules == []


def test_module_selector_supports_multi_module_routing():
    result = ModuleSelector().select(
        IntentResult(
            intent="multi_module",
            confidence=0.9,
            target_modules=[CAREER, ACADEMIC_PLANNING],
        )
    )

    assert result.selected_modules == [CAREER, ACADEMIC_PLANNING]


def test_module_selector_tracks_registry_availability():
    registry = ModuleRegistry()
    registry.register(FakeModule(ACADEMIC_PLANNING))

    result = ModuleSelector(registry=registry).select(
        IntentResult(
            intent="multi_module",
            confidence=0.9,
            target_modules=[ACADEMIC_PLANNING, CAREER],
        )
    )

    assert result.selected_modules == [ACADEMIC_PLANNING, CAREER]
    assert result.unavailable_modules == [CAREER]


def test_module_selector_rejects_unknown_module_names():
    result = ModuleSelector().select(
        IntentResult(
            intent="unknown",
            confidence=0.5,
            target_modules=["course_intelligence", CAREER],
        )
    )

    assert result.selected_modules == [CAREER]
    assert result.invalid_modules == ["course_intelligence"]


def test_module_selector_allows_reference_example_module():
    result = ModuleSelector().select(
        IntentResult(
            intent="example",
            confidence=1.0,
            target_modules=[EXAMPLE_MODULE],
        )
    )

    assert result.selected_modules == [EXAMPLE_MODULE]
    assert result.invalid_modules == []
