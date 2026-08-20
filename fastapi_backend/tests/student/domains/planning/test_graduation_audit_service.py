import asyncio
import os
import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from app.student.domains.planning.services.graduation_audit_service import (
    GraduationAuditService,
)


class _Repository:
    def __init__(self, *, plan=None, catalog_courses=None):
        self.plan = plan
        self.catalog_courses = catalog_courses or []
        self.calls = []

    async def get_plan(self, db, plan_id):
        self.calls.append({"method": "get_plan", "plan_id": plan_id})
        if self.plan and plan_id == self.plan.plan_id:
            return self.plan
        return None

    async def list_program_courses(self, db, program_id):
        self.calls.append({"method": "list_program_courses", "program_id": program_id})
        return self.catalog_courses


def _program(*, required_credits=120):
    return SimpleNamespace(
        program_id=uuid.uuid4(),
        program_name="Computer Science",
        degree="Bachelor of Science",
        total_credit_hours=required_credits,
    )


def _course(program, code, *, credits=3):
    return SimpleNamespace(
        course_id=uuid.uuid4(),
        program_id=program.program_id,
        course_code=code,
        course_name=f"{code} Name",
        credits=credits,
    )


def _plan_course(course):
    return SimpleNamespace(
        id=uuid.uuid4(),
        course_id=course.course_id,
        course=course,
    )


def _plan(program, plan_courses):
    return SimpleNamespace(
        plan_id=uuid.uuid4(),
        program_id=program.program_id,
        program=program,
        courses=plan_courses,
    )


def test_graduation_audit_rejects_invalid_plan_uuid():
    repository = _Repository()
    service = GraduationAuditService(repository)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.get_audit(object(), "not-a-uuid"))

    assert exc_info.value.status_code == 400
    assert repository.calls == []


def test_graduation_audit_returns_404_when_plan_is_missing():
    repository = _Repository()
    service = GraduationAuditService(repository)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.get_audit(object(), str(uuid.uuid4())))

    assert exc_info.value.status_code == 404
    assert repository.calls[0]["method"] == "get_plan"


def test_graduation_audit_calculates_partial_plan_progress():
    program = _program(required_credits=120)
    intro = _course(program, "CS 101", credits=3)
    data_structures = _course(program, "CS 201", credits=4)
    algorithms = _course(program, "CS 301", credits=3)
    plan = _plan(program, [_plan_course(intro), _plan_course(data_structures)])
    service = GraduationAuditService(
        _Repository(
            plan=plan,
            catalog_courses=[intro, data_structures, algorithms],
        )
    )

    result = asyncio.run(service.get_audit(object(), str(plan.plan_id)))

    assert result["credits"] == {
        "planned": 7,
        "required": 120,
        "remaining": 113,
        "completion_percentage": 5.83,
    }
    assert result["courses"] == {
        "total_required": 3,
        "completed": 2,
        "missing": 1,
        "completion_percentage": 66.67,
    }
    assert result["graduation_ready"] is False
    assert result["missing_courses"] == [
        {
            "course_id": str(algorithms.course_id),
            "course_code": "CS 301",
            "course_name": "CS 301 Name",
        }
    ]


def test_graduation_audit_empty_plan_reports_all_catalog_courses_missing():
    program = _program(required_credits=6)
    intro = _course(program, "CS 101", credits=3)
    lab = _course(program, "CS 101L", credits=3)
    plan = _plan(program, [])
    service = GraduationAuditService(_Repository(plan=plan, catalog_courses=[intro, lab]))

    result = asyncio.run(service.get_audit(object(), str(plan.plan_id)))

    assert result["credits"]["planned"] == 0
    assert result["credits"]["remaining"] == 6
    assert result["courses"]["completed"] == 0
    assert result["courses"]["missing"] == 2
    assert result["courses"]["completion_percentage"] == 0.0
    assert result["graduation_ready"] is False
    assert [course["course_code"] for course in result["missing_courses"]] == [
        "CS 101",
        "CS 101L",
    ]


def test_graduation_audit_ready_when_all_courses_and_credits_are_complete():
    program = _program(required_credits=6)
    intro = _course(program, "CS 101", credits=3)
    lab = _course(program, "CS 101L", credits=3)
    plan = _plan(program, [_plan_course(intro), _plan_course(lab)])
    service = GraduationAuditService(_Repository(plan=plan, catalog_courses=[intro, lab]))

    result = asyncio.run(service.get_audit(object(), str(plan.plan_id)))

    assert result["credits"]["planned"] == 6
    assert result["credits"]["remaining"] == 0
    assert result["credits"]["completion_percentage"] == 100.0
    assert result["courses"]["completion_percentage"] == 100.0
    assert result["missing_courses"] == []
    assert result["graduation_ready"] is True


def test_graduation_audit_percentages_clamp_to_100():
    program = _program(required_credits=3)
    capstone = _course(program, "CS 499", credits=6)
    plan = _plan(program, [_plan_course(capstone)])
    service = GraduationAuditService(_Repository(plan=plan, catalog_courses=[capstone]))

    result = asyncio.run(service.get_audit(object(), str(plan.plan_id)))

    assert result["credits"]["completion_percentage"] == 100.0
    assert result["courses"]["completion_percentage"] == 100.0
    assert result["graduation_ready"] is True


def test_graduation_audit_route_is_registered():
    os.environ["DEBUG"] = "true"
    from app.student.domains.planning.api.graduation_audit import router

    routes = [
        route for route in router.routes if isinstance(route, APIRoute) and "GET" in route.methods
    ]

    assert any(route.path == "/plans/{plan_id}/audit" for route in routes)
