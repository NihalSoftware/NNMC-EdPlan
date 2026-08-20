from __future__ import annotations

import pytest

from app.orchestrator.router.intent_router import IntentRouter
from app.orchestrator.router.module_selector import (
    ACADEMIC_PLANNING,
    ACADEMIC_SUCCESS,
    CAREER,
    COLLEGE_COMPARISON,
    FINANCE,
    SCHEDULING,
)
from app.orchestrator.schemas.student_context import StudentContext


@pytest.mark.parametrize(
    ("query", "expected_intent", "expected_modules"),
    [
        (
            "What courses should I take next semester?",
            "academic_planning",
            [ACADEMIC_PLANNING],
        ),
        ("Build my Spring schedule", "schedule_generation", [SCHEDULING]),
        ("What careers align with AI and Machine Learning?", "career_guidance", [CAREER]),
        ("Find scholarships for computer science students", "finance_assistance", [FINANCE]),
        ("My GPA is falling", "academic_success", [ACADEMIC_SUCCESS]),
        ("Compare two NNMC programs", "college_comparison", [COLLEGE_COMPARISON]),
        ("Recommend careers and scholarships", "multi_module", [CAREER, FINANCE]),
        ("Can you explain how EdPlan works?", "general_question", []),
    ],
)
def test_intent_router_classifies_supported_queries(
    query: str, expected_intent: str, expected_modules: list[str]
):
    result = IntentRouter().route(query, StudentContext())

    assert result.intent == expected_intent
    assert result.target_modules == expected_modules
    assert 0.0 <= result.confidence <= 1.0


def test_intent_router_general_question_has_low_confidence():
    result = IntentRouter().route("Can you explain how EdPlan works?", StudentContext())

    assert result.intent == "general_question"
    assert result.confidence == 0.35
    assert result.target_modules == []
