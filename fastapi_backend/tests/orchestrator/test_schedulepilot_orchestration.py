from __future__ import annotations

from datetime import date, time
from uuid import uuid4

import pytest

from app.models.agentic import ModuleExecution, OrchestratorRun, WorkflowEvent
from app.orchestrator.modules.module_registry import ModuleRegistry
from app.orchestrator.observability.run_tracker import COMPLETED
from app.orchestrator.observability.workflow_tracker import (
    MODULE_EXECUTION_COMPLETED,
    MODULE_EXECUTION_STARTED,
)
from app.orchestrator.router.module_selector import SCHEDULING
from app.orchestrator.schemas.student_context import StudentContext
from app.orchestrator.services.student_orchestrator import StudentOrchestrator
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
            preferences=[{"key": "class_preference", "value": "morning classes"}],
        )


class FakeRetrievalService:
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


@pytest.mark.asyncio
async def test_student_orchestrator_registers_schedulepilot_with_db_session():
    orchestrator = StudentOrchestrator(
        db=FakeAsyncSession(),
        context_loader=FakeContextLoader(),
    )

    assert orchestrator.module_registry.exists("scheduling") is True
    assert SCHEDULING == "scheduling"


@pytest.mark.asyncio
async def test_student_orchestrator_executes_schedulepilot_for_scheduling_intent():
    session = FakeAsyncSession()
    retrieval_service = FakeRetrievalService()
    registry = ModuleRegistry()
    registry.register(SchedulePilotModule(db=session, retrieval_service=retrieval_service))
    plan_id = uuid4()
    orchestrator = StudentOrchestrator(
        db=session,
        context_loader=FakeContextLoader(),
        module_registry=registry,
    )

    response = await orchestrator.run(
        user_id=1,
        plan_id=plan_id,
        query="Build my Spring schedule.",
    )

    assert response.message == "success"
    assert response.metadata["intent"]["intent"] == "schedule_generation"
    assert response.metadata["intent"]["target_modules"] == ["scheduling"]
    assert response.metadata["results"][0]["error"] is None
    assert response.module_responses[0].module_name == "scheduling"
    assert response.module_responses[0].metadata["implementation_phase"] == "Phase 3C"
    assert response.module_responses[0].metadata["status"] == "options_ranked"
    assert response.module_responses[0].metadata["counts"]["candidates"] == 1
    assert response.module_responses[0].metadata["counts"]["scored_candidates"] == 1
    assert response.module_responses[0].metadata["counts"]["ranked_options"] == 1
    assert response.module_responses[0].metadata["counts"]["feasible_candidates"] == 1
    assert response.module_responses[0].data["plan"]["plan_id"] == str(plan_id)
    assert response.module_responses[0].data["candidates"][0]["candidate_id"] == (
        "candidate-000001"
    )
    assert response.module_responses[0].data["candidates"][0]["is_feasible"] is True
    assert response.module_responses[0].data["candidates"][0]["metrics"]["total_credits"] == 3
    assert (
        response.module_responses[0].data["candidates"][0]["metrics_summary"]["metric_version"]
        == "1.0"
    )
    assert response.module_responses[0].data["candidates"][0]["normalized_score"] == 58.0
    assert response.module_responses[0].data["candidates"][0]["scoring_summary"][
        "satisfied_preferences"
    ] == ["morning_classes"]
    assert response.module_responses[0].data["scored_candidates"][0]["candidate_id"] == (
        "candidate-000001"
    )
    assert response.module_responses[0].data["ranked_options"][0]["option_id"] == (
        "schedule-option-000001"
    )
    assert response.module_responses[0].data["ranked_options"][0]["rank"] == 1
    assert response.module_responses[0].data["ranked_options"][0]["normalized_score"] == 58.0
    assert response.module_responses[0].data["top_option"]["option_id"] == (
        "schedule-option-000001"
    )
    assert response.module_responses[0].data["validation_metadata"]["validated_count"] == 1
    assert response.module_responses[0].data["metrics_metadata"]["candidate_count"] == 1
    assert response.module_responses[0].data["scoring_metadata"]["candidate_count"] == 1
    assert response.module_responses[0].data["ranking_metadata"]["returned_candidates"] == 1
    assert "Module not yet implemented" not in str(response.model_dump())
    assert retrieval_service.calls == [(session, 1, str(plan_id))]

    run = next(item for item in session.added if isinstance(item, OrchestratorRun))
    execution = next(item for item in session.added if isinstance(item, ModuleExecution))
    event_types = [item.event_type for item in session.added if isinstance(item, WorkflowEvent)]

    assert run.status == COMPLETED
    assert run.selected_modules == ["scheduling"]
    assert execution.module_name == "scheduling"
    assert execution.success is True
    assert MODULE_EXECUTION_STARTED in event_types
    assert MODULE_EXECUTION_COMPLETED in event_types
