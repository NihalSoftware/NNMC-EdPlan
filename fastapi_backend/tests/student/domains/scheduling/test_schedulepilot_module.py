from __future__ import annotations

from datetime import date, time

import pytest

from app.orchestrator.execution.module_executor import ModuleExecutor
from app.orchestrator.modules.module_registry import ModuleRegistry
from app.orchestrator.schemas.student_context import StudentContext
from app.student.domains.scheduling import module
from app.student.domains.scheduling.engine import CandidateGenerator
from app.student.domains.scheduling.module import SchedulePilotModule
from app.student.domains.scheduling.schemas.schedulepilot import (
    ScheduleCourse,
    ScheduleCourseOffering,
    ScheduleMeeting,
    ScheduleRetrievalContext,
    ScheduleSection,
    ScheduleStudentPlan,
    ScheduleTerm,
)


class _RetrievalService:
    def __init__(self):
        self.calls = []

    async def build_context(self, db, *, user_id, plan_id):
        self.calls.append((db, user_id, plan_id))
        term = ScheduleTerm(
            term_id="term-1",
            term_name="Fall 2026",
            start_date=date(2026, 8, 17),
            end_date=date(2026, 12, 11),
            is_active=True,
        )
        return ScheduleRetrievalContext(
            plan=ScheduleStudentPlan(
                plan_id=plan_id,
                user_id=user_id,
                university_id="university-1",
                program_id="program-1",
                plan_name="Primary Plan",
                is_active=True,
            ),
            courses=[
                ScheduleCourse(
                    plan_course_id="pc-1",
                    plan_id=plan_id,
                    course_id="course-1",
                    planned_term_id="term-1",
                    status="Planned",
                    course_code="CS 101",
                    course_name="Intro",
                    credits=3,
                    lecture_hours=3,
                    lab_hours=0,
                )
            ],
            terms=[term],
            offerings=[
                ScheduleCourseOffering(
                    offering_id="offering-1",
                    course_id="course-1",
                    term_id="term-1",
                    offering_type="Lecture",
                    course_code="CS 101",
                    course_name="Intro",
                    credits=3,
                    term=term,
                )
            ],
            sections=[
                ScheduleSection(
                    section_id="section-1",
                    offering_id="offering-1",
                    course_id="course-1",
                    term_id="term-1",
                    offering_type="Lecture",
                    section_number="001",
                    crn="12345",
                    instruction_method="In Person",
                    capacity=30,
                    enrolled=10,
                    available_seats=20,
                    status="Open",
                )
            ],
            meetings=[
                ScheduleMeeting(
                    meeting_id="meeting-1",
                    section_id="section-1",
                    weekday=1,
                    start_time=time(9, 0),
                    end_time=time(10, 15),
                    meeting_type="Class",
                    is_async=False,
                )
            ],
        )


def test_schedulepilot_module_metadata():
    assert module.MODULE_NAME == "scheduling"
    assert module.MODULE_DESCRIPTION == "Build and explain student course schedules."
    assert module.IMPLEMENTATION_PHASE == "Phase 3C"


@pytest.mark.asyncio
async def test_schedulepilot_module_returns_phase_3c_ranked_options_response():
    service = _RetrievalService()
    db = object()
    response = await SchedulePilotModule(
        db=db,
        retrieval_service=service,
        candidate_generator=CandidateGenerator(),
    ).execute(
        StudentContext(
            user={"id": 1},
            plan={"plan_id": "plan-1"},
            preferences=[{"key": "class_preference", "value": "morning classes"}],
        ),
        "Build my Spring schedule.",
    )

    assert response.module_name == "scheduling"
    assert "generated, validated, scored, and ranked" in response.content
    assert "Persistence and schedule activation" in response.content
    assert response.metadata["module_version"] == module.MODULE_VERSION
    assert response.metadata["implementation_phase"] == "Phase 3C"
    assert response.metadata["status"] == "options_ranked"
    assert response.metadata["counts"]["courses"] == 1
    assert response.metadata["counts"]["candidates"] == 1
    assert response.metadata["counts"]["scored_candidates"] == 1
    assert response.metadata["counts"]["ranked_options"] == 1
    assert response.metadata["counts"]["feasible_candidates"] == 1
    assert response.metadata["counts"]["infeasible_candidates"] == 0
    assert response.metadata["candidate_generation_implemented"] is True
    assert response.metadata["conflict_detection_implemented"] is True
    assert response.metadata["feasibility_validation_implemented"] is True
    assert response.metadata["metrics_implemented"] is True
    assert response.metadata["scoring_implemented"] is True
    assert response.metadata["ranking_implemented"] is True
    assert response.data["plan"]["plan_id"] == "plan-1"
    assert response.data["candidates"][0]["candidate_id"] == "candidate-000001"
    assert response.data["candidates"][0]["is_feasible"] is True
    assert response.data["candidates"][0]["metrics"]["total_credits"] == 3
    assert response.data["candidates"][0]["metrics"]["lecture_count"] == 1
    assert response.data["candidates"][0]["metrics_summary"]["metric_version"] == "1.0"
    assert response.data["candidates"][0]["score"] == 58.0
    assert response.data["candidates"][0]["normalized_score"] == 58.0
    assert response.data["candidates"][0]["scoring_summary"]["satisfied_preferences"] == [
        "morning_classes"
    ]
    assert response.data["candidates"][0]["conflicts"] == []
    assert response.data["candidates"][0]["validation_summary"]["conflict_count"] == 0
    assert response.data["scored_candidates"][0]["candidate_id"] == "candidate-000001"
    assert response.data["ranked_options"][0]["option_id"] == "schedule-option-000001"
    assert response.data["ranked_options"][0]["rank"] == 1
    assert response.data["ranked_options"][0]["normalized_score"] == 58.0
    assert response.data["ranked_options"][0]["metadata"]["source_candidate_id"] == (
        "candidate-000001"
    )
    assert response.data["top_option"]["option_id"] == "schedule-option-000001"
    assert response.data["generation_metadata"]["generated_count"] == 1
    assert response.data["validation_metadata"]["validated_count"] == 1
    assert response.data["validation_metadata"]["feasible_count"] == 1
    assert response.data["metrics_metadata"]["candidate_count"] == 1
    assert response.data["metrics_metadata"]["metric_version"] == "1.0"
    assert response.data["scoring_metadata"]["candidate_count"] == 1
    assert response.data["scoring_metadata"]["scoring_version"] == "1.0"
    assert response.data["scoring_metadata"]["preference_count"] == 1
    assert response.data["ranking_metadata"]["evaluated_candidates"] == 1
    assert response.data["ranking_metadata"]["feasible_candidates"] == 1
    assert response.data["ranking_metadata"]["returned_candidates"] == 1
    assert response.data["ranking_metadata"]["ranking_version"] == "1.0"
    assert service.calls == [(db, 1, "plan-1")]


@pytest.mark.asyncio
async def test_schedulepilot_module_requires_database_session():
    response = await SchedulePilotModule().execute(
        StudentContext(user={"id": 1}, plan={"plan_id": "plan-1"}),
        "Build my Spring schedule.",
    )

    assert response.metadata["status"] == "error"
    assert response.metadata["error"] == "database_session_required"


@pytest.mark.asyncio
async def test_schedulepilot_module_requires_loaded_student_context():
    response = await SchedulePilotModule(db=object()).execute(
        StudentContext(),
        "Build my Spring schedule.",
    )

    assert response.metadata["status"] == "error"
    assert response.metadata["error"] == "student_context_required"


@pytest.mark.asyncio
async def test_module_executor_executes_schedulepilot_without_not_implemented_error():
    registry = ModuleRegistry()
    registry.register(SchedulePilotModule(db=object(), retrieval_service=_RetrievalService()))

    result = await ModuleExecutor(registry).execute_by_name(
        "scheduling",
        StudentContext(user={"id": 1}, plan={"plan_id": "plan-1"}),
        "Build my Spring schedule.",
    )

    assert result.success is True
    assert result.error is None
    assert result.response is not None
    assert result.response.module_name == "scheduling"
    assert result.response.metadata["status"] == "options_ranked"
