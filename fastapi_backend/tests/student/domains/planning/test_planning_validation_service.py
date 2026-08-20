import asyncio
import os
import uuid
from datetime import date
from types import SimpleNamespace

from fastapi.routing import APIRoute

from app.student.domains.planning.schemas.planning_validation import (
    PlanCourseValidationRequest,
)
from app.student.domains.planning.services.planning_validation_service import (
    PlanningValidationService,
)


class _Repository:
    def __init__(
        self,
        *,
        plan,
        prerequisites=None,
        corequisites=None,
        courses=None,
        terms=None,
    ):
        self.plan = plan
        self.prerequisites = prerequisites or []
        self.corequisites = corequisites or []
        self.courses = courses or {}
        self.terms = terms or {}

    async def get_plan(self, db, plan_id):
        return self.plan if plan_id == self.plan.plan_id else None

    async def get_course(self, db, course_id):
        return self.courses.get(course_id)

    async def get_term(self, db, term_id):
        return self.terms.get(term_id)

    async def list_prerequisite_links(self, db, course_ids):
        ids = set(course_ids)
        return [link for link in self.prerequisites if link.course_id in ids]

    async def list_corequisite_links(self, db, course_ids):
        ids = set(course_ids)
        return [link for link in self.corequisites if link.course_id in ids]


def _course(code, *, credits=3):
    return SimpleNamespace(
        course_id=uuid.uuid4(),
        course_code=code,
        course_name=code,
        credits=credits,
    )


def _term(name, start, end):
    return SimpleNamespace(
        term_id=uuid.uuid4(),
        term_name=name,
        start_date=start,
        end_date=end,
    )


def _plan_course(course, term):
    return SimpleNamespace(
        id=uuid.uuid4(),
        plan_id=None,
        course_id=course.course_id,
        planned_term_id=term.term_id if term else None,
        status="Planned",
        course=course,
        planned_term=term,
    )


def _plan(plan_courses):
    plan_id = uuid.uuid4()
    for plan_course in plan_courses:
        plan_course.plan_id = plan_id
    return SimpleNamespace(plan_id=plan_id, courses=plan_courses)


def _prerequisite(course, prerequisite):
    return SimpleNamespace(
        course_id=course.course_id,
        prerequisite_course_id=prerequisite.course_id,
        prerequisite_course=prerequisite,
    )


def _corequisite(course, corequisite):
    return SimpleNamespace(
        course_id=course.course_id,
        corequisite_course_id=corequisite.course_id,
        corequisite_course=corequisite,
    )


def test_validate_plan_returns_all_duplicate_and_credit_issues():
    heavy_course = _course("CS 401", credits=10)
    fall = _term("Fall 2026", date(2026, 8, 17), date(2026, 12, 11))
    plan = _plan(
        [
            _plan_course(heavy_course, fall),
            _plan_course(heavy_course, fall),
        ]
    )
    service = PlanningValidationService(_Repository(plan=plan))

    result = asyncio.run(service.validate_plan(object(), str(plan.plan_id)))

    assert result["is_valid"] is False
    assert [issue["code"] for issue in result["issues"]] == [
        "DUPLICATE_COURSE_IN_PLAN",
        "TERM_CREDIT_LIMIT_EXCEEDED",
    ]
    assert result["summary"]["error_count"] == 2
    assert result["issues"][1]["metadata"]["term_credits"] == 20
    assert result["issues"][1]["metadata"]["max_term_credits"] == 18


def test_projected_prerequisite_in_earlier_term_satisfies_future_course():
    intro = _course("CS 101")
    advanced = _course("CS 201")
    fall = _term("Fall 2026", date(2026, 8, 17), date(2026, 12, 11))
    spring = _term("Spring 2027", date(2027, 1, 12), date(2027, 5, 8))
    plan = _plan(
        [
            _plan_course(intro, fall),
            _plan_course(advanced, spring),
        ]
    )
    repository = _Repository(
        plan=plan,
        prerequisites=[_prerequisite(advanced, intro)],
    )
    service = PlanningValidationService(repository)

    result = asyncio.run(service.validate_plan(object(), str(plan.plan_id)))

    assert result["is_valid"] is True
    assert result["issues"] == []


def test_prerequisite_in_same_term_returns_error():
    intro = _course("CS 101")
    advanced = _course("CS 201")
    fall = _term("Fall 2026", date(2026, 8, 17), date(2026, 12, 11))
    plan = _plan(
        [
            _plan_course(intro, fall),
            _plan_course(advanced, fall),
        ]
    )
    service = PlanningValidationService(
        _Repository(plan=plan, prerequisites=[_prerequisite(advanced, intro)])
    )

    result = asyncio.run(service.validate_plan(object(), str(plan.plan_id)))

    assert result["is_valid"] is False
    assert result["issues"][0]["code"] == "PREREQUISITE_NOT_SATISFIED"
    assert result["issues"][0]["course_code"] == "CS 201"
    assert result["issues"][0]["related_course_codes"] == ["CS 101"]


def test_corequisite_must_be_scheduled_in_same_term():
    lecture = _course("CHEM 121")
    lab = _course("CHEM 121L")
    fall = _term("Fall 2026", date(2026, 8, 17), date(2026, 12, 11))
    spring = _term("Spring 2027", date(2027, 1, 12), date(2027, 5, 8))
    plan = _plan(
        [
            _plan_course(lecture, fall),
            _plan_course(lab, spring),
        ]
    )
    service = PlanningValidationService(
        _Repository(plan=plan, corequisites=[_corequisite(lecture, lab)])
    )

    result = asyncio.run(service.validate_plan(object(), str(plan.plan_id)))

    assert result["is_valid"] is False
    assert result["issues"][0]["code"] == "COREQUISITE_NOT_SCHEDULED_SAME_TERM"
    assert result["issues"][0]["course_code"] == "CHEM 121"
    assert result["issues"][0]["related_course_codes"] == ["CHEM 121L"]


def test_validate_course_add_operation_checks_candidate_against_existing_plan():
    intro = _course("CS 101")
    fall = _term("Fall 2026", date(2026, 8, 17), date(2026, 12, 11))
    plan = _plan([_plan_course(intro, fall)])
    repository = _Repository(
        plan=plan,
        courses={intro.course_id: intro},
        terms={fall.term_id: fall},
    )
    service = PlanningValidationService(repository)
    payload = PlanCourseValidationRequest(
        course_id=str(intro.course_id),
        planned_term_id=str(fall.term_id),
    )

    result = asyncio.run(service.validate_course(object(), str(plan.plan_id), payload))

    assert result["is_valid"] is False
    assert result["issues"][0]["code"] == "DUPLICATE_COURSE_IN_PLAN"
    assert result["issues"][0]["metadata"]["occurrences"] == 2


def test_validation_routes_are_registered():
    os.environ["DEBUG"] = "true"
    from app.student.domains.planning.api.normalized_plans import router

    post_paths = {
        route.path
        for route in router.routes
        if isinstance(route, APIRoute) and "POST" in route.methods
    }

    assert "/plans/{plan_id}/validate" in post_paths
    assert "/plans/{plan_id}/validate-course" in post_paths
