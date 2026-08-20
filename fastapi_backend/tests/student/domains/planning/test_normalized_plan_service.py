import asyncio
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.student.domains.planning.schemas.normalized_plan import (
    PlanCourseCreateRequest,
    PlanCourseUpdateRequest,
    PlanCreateRequest,
    PlanUpdateRequest,
)
from app.student.domains.planning.services.normalized_plan_service import (
    MAX_TERM_CREDITS,
    NormalizedPlanService,
)


class _Db:
    def __init__(self):
        self.commits = 0
        self.rollbacks = 0

    async def commit(self):
        self.commits += 1

    async def rollback(self):
        self.rollbacks += 1


class _PlanRepository:
    def __init__(self):
        self.calls = []
        self.plan_id = uuid.uuid4()
        self.plan_model = SimpleNamespace(plan_id=self.plan_id, is_active=True)
        self.plan_payload = {
            "plan_id": str(self.plan_id),
            "user_id": 42,
            "university_id": str(uuid.uuid4()),
            "program_id": str(uuid.uuid4()),
            "plan_name": "Primary Plan",
            "description": None,
            "is_active": True,
            "max_term_credits": MAX_TERM_CREDITS,
            "term_credit_totals": [],
            "courses": [],
        }

    async def list_plans(self, db, *, user_id=None, is_active=None):
        self.calls.append({"method": "list_plans", "user_id": user_id, "is_active": is_active})
        return [self.plan_payload]

    async def create_plan(self, db, **kwargs):
        self.calls.append({"method": "create_plan", **kwargs})
        self.plan_model.plan_id = self.plan_id
        return self.plan_model

    async def get_plan_by_id(self, db, plan_id):
        self.calls.append({"method": "get_plan_by_id", "plan_id": str(plan_id)})
        return self.plan_payload

    async def get_plan_model(self, db, plan_id, *, include_courses=False):
        self.calls.append(
            {
                "method": "get_plan_model",
                "plan_id": str(plan_id),
                "include_courses": include_courses,
            }
        )
        return self.plan_model

    async def update_plan(self, plan, **kwargs):
        self.calls.append({"method": "update_plan", **kwargs})
        if kwargs.get("plan_name") is not None:
            plan.plan_name = kwargs["plan_name"]
        if kwargs.get("is_active") is not None:
            plan.is_active = kwargs["is_active"]
        return plan

    async def deactivate_plan(self, plan):
        self.calls.append({"method": "deactivate_plan"})
        plan.is_active = False
        return plan


class _MissingPlanRepository(_PlanRepository):
    async def get_plan_model(self, db, plan_id, *, include_courses=False):
        self.calls.append(
            {
                "method": "get_plan_model",
                "plan_id": str(plan_id),
                "include_courses": include_courses,
            }
        )
        return None


class _PlanCourseRepository:
    def __init__(self):
        self.calls = []
        self.plan_course_model = SimpleNamespace(id=uuid.uuid4())
        self.plan_course_payload = {
            "id": str(self.plan_course_model.id),
            "plan_id": str(uuid.uuid4()),
            "course_id": str(uuid.uuid4()),
            "planned_term_id": None,
            "status": "Planned",
            "notes": None,
            "course": {"credits": 3},
            "planned_term": None,
        }

    async def list_plan_courses(self, db, plan_id):
        self.calls.append({"method": "list_plan_courses", "plan_id": plan_id})
        return [self.plan_course_payload]

    async def get_plan_course_model(self, db, *, plan_id, course_id):
        self.calls.append(
            {
                "method": "get_plan_course_model",
                "plan_id": plan_id,
                "course_id": course_id,
            }
        )
        return self.plan_course_model

    async def get_plan_course(self, db, *, plan_id, course_id):
        self.calls.append({"method": "get_plan_course", "plan_id": plan_id, "course_id": course_id})
        return self.plan_course_payload

    async def add_plan_course(self, db, **kwargs):
        self.calls.append({"method": "add_plan_course", **kwargs})
        return self.plan_course_model

    async def update_plan_course(self, plan_course, **kwargs):
        self.calls.append({"method": "update_plan_course", **kwargs})
        return plan_course

    async def delete_plan_course(self, db, plan_course):
        self.calls.append({"method": "delete_plan_course", "plan_course": plan_course})


def test_plan_service_creates_plan_with_uuid_identifiers():
    plan_repository = _PlanRepository()
    course_repository = _PlanCourseRepository()
    service = NormalizedPlanService(plan_repository, course_repository)
    db = _Db()
    university_id = str(uuid.uuid4())
    program_id = str(uuid.uuid4())
    payload = PlanCreateRequest(
        user_id=42,
        university_id=university_id,
        program_id=program_id,
        plan_name=" Primary Plan ",
    )

    result = asyncio.run(service.create_plan(db, payload))

    create_call = plan_repository.calls[0]
    assert result == plan_repository.plan_payload
    assert create_call["university_id"] == uuid.UUID(university_id)
    assert create_call["program_id"] == uuid.UUID(program_id)
    assert create_call["plan_name"] == "Primary Plan"
    assert db.commits == 1
    assert db.rollbacks == 0


def test_plan_service_rejects_invalid_plan_uuid_without_repository_call():
    plan_repository = _PlanRepository()
    service = NormalizedPlanService(plan_repository, _PlanCourseRepository())

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.get_plan_by_id(object(), "not-a-uuid"))

    assert exc_info.value.status_code == 400
    assert plan_repository.calls == []


def test_plan_service_updates_nullable_description_and_active_state():
    plan_repository = _PlanRepository()
    service = NormalizedPlanService(plan_repository, _PlanCourseRepository())
    db = _Db()
    plan_id = str(plan_repository.plan_id)
    payload = PlanUpdateRequest(description=None, is_active=False)

    asyncio.run(service.update_plan(db, plan_id, payload))

    update_call = next(call for call in plan_repository.calls if call["method"] == "update_plan")
    assert update_call["description"] is None
    assert update_call["update_description"] is True
    assert update_call["is_active"] is False
    assert db.commits == 1


def test_plan_service_deactivates_plan_instead_of_hard_delete():
    plan_repository = _PlanRepository()
    service = NormalizedPlanService(plan_repository, _PlanCourseRepository())
    db = _Db()

    asyncio.run(service.deactivate_plan(db, str(plan_repository.plan_id)))

    assert plan_repository.plan_model.is_active is False
    assert {"method": "deactivate_plan"} in plan_repository.calls
    assert db.commits == 1


def test_plan_course_service_adds_course_without_credit_blocking():
    plan_repository = _PlanRepository()
    course_repository = _PlanCourseRepository()
    service = NormalizedPlanService(plan_repository, course_repository)
    db = _Db()
    plan_id = str(plan_repository.plan_id)
    course_id = str(uuid.uuid4())
    term_id = str(uuid.uuid4())
    payload = PlanCourseCreateRequest(
        course_id=course_id,
        planned_term_id=term_id,
        status="Planned",
        notes="Manual planning only.",
    )

    result = asyncio.run(service.add_plan_course(db, plan_id, payload))

    add_call = next(call for call in course_repository.calls if call["method"] == "add_plan_course")
    assert result == course_repository.plan_course_payload
    assert add_call["plan_id"] == uuid.UUID(plan_id)
    assert add_call["course_id"] == uuid.UUID(course_id)
    assert add_call["planned_term_id"] == uuid.UUID(term_id)
    assert db.commits == 1


def test_plan_course_service_can_move_course_to_unscheduled_bucket():
    plan_repository = _PlanRepository()
    course_repository = _PlanCourseRepository()
    service = NormalizedPlanService(plan_repository, course_repository)
    db = _Db()
    plan_id = str(plan_repository.plan_id)
    course_id = str(uuid.uuid4())
    payload = PlanCourseUpdateRequest(planned_term_id=None, notes=None)

    asyncio.run(service.update_plan_course(db, plan_id, course_id, payload))

    update_call = next(
        call for call in course_repository.calls if call["method"] == "update_plan_course"
    )
    assert update_call["planned_term_id"] is None
    assert update_call["update_planned_term"] is True
    assert update_call["notes"] is None
    assert update_call["update_notes"] is True
    assert db.commits == 1


def test_plan_course_service_raises_404_when_plan_is_missing():
    service = NormalizedPlanService(_MissingPlanRepository(), _PlanCourseRepository())

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.list_plan_courses(object(), str(uuid.uuid4())))

    assert exc_info.value.status_code == 404
