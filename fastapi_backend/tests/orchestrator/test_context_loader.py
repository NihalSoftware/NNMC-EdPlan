from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.models.agentic import ConversationMemory, StudentPreference
from app.models.education_plan import CourseSchedule, EducationPlan, ProgramCourse
from app.models.user import User, UserRole
from app.orchestrator.context.context_loader import (
    ContextLoader,
    PlanNotFoundError,
    ProgramNotFoundError,
    UniversityNotFoundError,
    UserNotFoundError,
)
from app.student.domains.planning.models import EdPlan


class FakeScalarResult:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items


class FakeResult:
    def __init__(self, scalar=None, items=None):
        self.scalar = scalar
        self.items = items or []

    def scalar_one_or_none(self):
        return self.scalar

    def scalars(self):
        return FakeScalarResult(self.items)


class FakeAsyncSession:
    def __init__(self, results):
        self.results = list(results)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        if not self.results:
            raise AssertionError("Unexpected database query")
        return self.results.pop(0)


def build_user() -> User:
    return User(
        id=1,
        email="student@example.com",
        password_hash="hashed",
        first_name="Ada",
        last_name="Lovelace",
        phone_number="555-0100",
        role=UserRole.CUSTOMER,
        is_active=True,
        is_deactivated=False,
    )


def build_operational_plan() -> EducationPlan:
    plan = EducationPlan(
        id=10,
        user_id=1,
        program_name="Computer Science",
        university_name="Example University",
        degree="BS",
        payload={"degree": "BS"},
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    plan.courses = [
        ProgramCourse(
            id=20,
            education_plan_id=10,
            year_label="Year 1",
            semester_label="Fall",
            course_code="CS101",
            course_name="Intro to CS",
            credits=3,
            prerequisite=None,
            corequisite=None,
            schedule={"day": "Monday", "time": "09:00"},
        )
    ]
    return plan


def build_plan(plan_id) -> EdPlan:
    return EdPlan(
        plan_id=plan_id,
        user_id=1,
        university_id=uuid4(),
        program_id=uuid4(),
        plan_name="Primary Plan",
    )


@pytest.mark.asyncio
async def test_load_student_context_successfully():
    plan_id = uuid4()
    run_id = uuid4()
    preference_id = uuid4()
    memory_id = uuid4()
    operational_plan = build_operational_plan()
    session = FakeAsyncSession(
        [
            FakeResult(scalar=build_user()),
            FakeResult(scalar=build_plan(plan_id)),
            FakeResult(scalar=operational_plan),
            FakeResult(
                items=[
                    CourseSchedule(
                        id=30,
                        education_plan_id=10,
                        course_id=20,
                        day="Monday",
                        time="09:00",
                        available=True,
                    )
                ]
            ),
            FakeResult(
                items=[
                    StudentPreference(
                        preference_id=preference_id,
                        user_id=1,
                        preference_key="career_goal",
                        preference_value="Software Engineer",
                        updated_at=datetime(2026, 1, 3, tzinfo=UTC),
                    )
                ]
            ),
            FakeResult(
                items=[
                    ConversationMemory(
                        memory_id=memory_id,
                        user_id=1,
                        plan_id=plan_id,
                        run_id=run_id,
                        summary="Student prefers project-based courses.",
                        created_at=datetime(2026, 1, 4, tzinfo=UTC),
                    )
                ]
            ),
        ]
    )

    context = await ContextLoader(session).load(1, plan_id, "What should I take next?")

    assert context.user["email"] == "student@example.com"
    assert context.plan["plan_id"] == str(plan_id)
    assert context.program == {"name": "Computer Science", "degree": "BS"}
    assert context.university == {"name": "Example University"}
    assert context.completed_courses[0]["code"] == "CS101"
    assert context.completed_courses[0]["available_schedules"][0]["day"] == "Monday"
    assert context.preferences[0]["key"] == "career_goal"
    assert context.memory[0]["summary"] == "Student prefers project-based courses."
    assert context.career_goal == "Software Engineer"


@pytest.mark.asyncio
async def test_load_student_context_missing_user():
    session = FakeAsyncSession([FakeResult(scalar=None)])

    with pytest.raises(UserNotFoundError):
        await ContextLoader(session).load(999, uuid4(), "Help me plan")


@pytest.mark.asyncio
async def test_load_student_context_missing_plan():
    session = FakeAsyncSession([FakeResult(scalar=build_user()), FakeResult(scalar=None)])

    with pytest.raises(PlanNotFoundError):
        await ContextLoader(session).load(1, uuid4(), "Help me plan")


@pytest.mark.asyncio
async def test_load_student_context_missing_program():
    plan_id = uuid4()
    session = FakeAsyncSession(
        [
            FakeResult(scalar=build_user()),
            FakeResult(scalar=build_plan(plan_id)),
            FakeResult(scalar=None),
        ]
    )

    with pytest.raises(ProgramNotFoundError):
        await ContextLoader(session).load(1, plan_id, "Help me plan")


@pytest.mark.asyncio
async def test_load_student_context_missing_university():
    plan_id = uuid4()
    operational_plan = build_operational_plan()
    operational_plan.university_name = ""
    session = FakeAsyncSession(
        [
            FakeResult(scalar=build_user()),
            FakeResult(scalar=build_plan(plan_id)),
            FakeResult(scalar=operational_plan),
        ]
    )

    with pytest.raises(UniversityNotFoundError):
        await ContextLoader(session).load(1, plan_id, "Help me plan")


@pytest.mark.asyncio
async def test_load_student_context_empty_preferences():
    plan_id = uuid4()
    session = FakeAsyncSession(
        [
            FakeResult(scalar=build_user()),
            FakeResult(scalar=build_plan(plan_id)),
            FakeResult(scalar=build_operational_plan()),
            FakeResult(items=[]),
            FakeResult(items=[]),
            FakeResult(items=[]),
        ]
    )

    context = await ContextLoader(session).load(1, plan_id, "Help me plan")

    assert context.preferences == []
    assert context.career_goal is None


@pytest.mark.asyncio
async def test_load_student_context_empty_memory():
    plan_id = uuid4()
    session = FakeAsyncSession(
        [
            FakeResult(scalar=build_user()),
            FakeResult(scalar=build_plan(plan_id)),
            FakeResult(scalar=build_operational_plan()),
            FakeResult(items=[]),
            FakeResult(
                items=[
                    StudentPreference(
                        preference_id=uuid4(),
                        user_id=1,
                        preference_key="format",
                        preference_value="concise",
                        updated_at=datetime(2026, 1, 3, tzinfo=UTC),
                    )
                ]
            ),
            FakeResult(items=[]),
        ]
    )

    context = await ContextLoader(session).load(1, plan_id, "Help me plan")

    assert context.memory == []
    assert context.preferences[0]["value"] == "concise"
