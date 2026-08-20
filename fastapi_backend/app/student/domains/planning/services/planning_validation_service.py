from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

# Initialize Base metadata before importing model packages from a cold route import.
from app.db.base import Base as _Base  # noqa: F401
from app.shared.constants.institution import NORTHERN_NEW_MEXICO_COLLEGE_NAME
from app.student.domains.discovery.models import (
    Course,
    CourseCorequisite,
    CoursePrerequisite,
    Program,
    University,
)
from app.student.domains.planning.models import EdPlan, PlanCourse
from app.student.domains.planning.schemas.planning_validation import (
    PlanCourseValidationRequest,
    PlanValidationRequest,
)
from app.student.domains.planning.services.normalized_plan_service import MAX_TERM_CREDITS
from app.student.domains.scheduling.models import AcademicTerm


def _parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}",
        ) from exc


@dataclass(frozen=True)
class _ValidationPlanCourse:
    id: uuid.UUID | None
    plan_id: uuid.UUID
    course_id: uuid.UUID
    planned_term_id: uuid.UUID | None
    status: str
    course: Course
    planned_term: AcademicTerm | None


class PlanningValidationRepository:
    async def get_plan(self, db: AsyncSession, plan_id: uuid.UUID) -> EdPlan | None:
        result = await db.execute(
            select(EdPlan)
            .options(
                selectinload(EdPlan.courses).joinedload(PlanCourse.course),
                selectinload(EdPlan.courses).joinedload(PlanCourse.planned_term),
            )
            .where(
                EdPlan.plan_id == plan_id,
                EdPlan.university.has(
                    University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
                ),
            )
        )
        return result.scalar_one_or_none()

    async def get_course(self, db: AsyncSession, course_id: uuid.UUID) -> Course | None:
        result = await db.execute(
            select(Course).where(
                Course.course_id == course_id,
                Course.program.has(
                    Program.university.has(
                        University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
                    )
                ),
            )
        )
        return result.scalar_one_or_none()

    async def get_term(self, db: AsyncSession, term_id: uuid.UUID) -> AcademicTerm | None:
        result = await db.execute(select(AcademicTerm).where(AcademicTerm.term_id == term_id))
        return result.scalar_one_or_none()

    async def list_prerequisite_links(
        self,
        db: AsyncSession,
        course_ids: Iterable[uuid.UUID],
    ) -> list[CoursePrerequisite]:
        ids = list(set(course_ids))
        if not ids:
            return []
        result = await db.execute(
            select(CoursePrerequisite)
            .options(joinedload(CoursePrerequisite.prerequisite_course))
            .where(CoursePrerequisite.course_id.in_(ids))
        )
        return list(result.scalars().all())

    async def list_corequisite_links(
        self,
        db: AsyncSession,
        course_ids: Iterable[uuid.UUID],
    ) -> list[CourseCorequisite]:
        ids = list(set(course_ids))
        if not ids:
            return []
        result = await db.execute(
            select(CourseCorequisite)
            .options(joinedload(CourseCorequisite.corequisite_course))
            .where(CourseCorequisite.course_id.in_(ids))
        )
        return list(result.scalars().all())


class PlanningValidationService:
    def __init__(
        self,
        repository: PlanningValidationRepository | None = None,
    ) -> None:
        self.repository = repository or PlanningValidationRepository()

    async def validate_plan(
        self,
        db: AsyncSession,
        plan_id: str,
        payload: PlanValidationRequest | None = None,
    ) -> dict:
        parsed_plan_id = _parse_uuid(plan_id, "plan_id")
        plan = await self.repository.get_plan(db, parsed_plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        return await self._validate_course_set(db, plan, _plan_courses_from_model(plan))

    async def validate_course(
        self,
        db: AsyncSession,
        plan_id: str,
        payload: PlanCourseValidationRequest,
    ) -> dict:
        parsed_plan_id = _parse_uuid(plan_id, "plan_id")
        parsed_course_id = _parse_uuid(payload.course_id, "course_id")
        parsed_term_id = (
            _parse_uuid(payload.planned_term_id, "planned_term_id")
            if payload.planned_term_id
            else None
        )

        plan = await self.repository.get_plan(db, parsed_plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

        course = await self.repository.get_course(db, parsed_course_id)
        if not course:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")

        term = None
        if parsed_term_id:
            term = await self.repository.get_term(db, parsed_term_id)
            if not term:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Term not found")

        candidate = _ValidationPlanCourse(
            id=None,
            plan_id=parsed_plan_id,
            course_id=parsed_course_id,
            planned_term_id=parsed_term_id,
            status=payload.status,
            course=course,
            planned_term=term,
        )
        plan_courses = _merge_candidate_course(
            _plan_courses_from_model(plan),
            candidate,
            operation=payload.operation,
        )
        return await self._validate_course_set(db, plan, plan_courses)

    async def _validate_course_set(
        self,
        db: AsyncSession,
        plan: EdPlan,
        plan_courses: Sequence[_ValidationPlanCourse],
    ) -> dict:
        course_ids = [plan_course.course_id for plan_course in plan_courses]
        prerequisite_links = await self.repository.list_prerequisite_links(db, course_ids)
        corequisite_links = await self.repository.list_corequisite_links(db, course_ids)

        issues: list[dict] = []
        issues.extend(_validate_duplicates(plan_courses))
        issues.extend(_validate_prerequisites(plan_courses, prerequisite_links))
        issues.extend(_validate_corequisites(plan_courses, corequisite_links))
        issues.extend(_validate_credits(plan_courses))
        return _validation_result(plan.plan_id, issues)


def _plan_courses_from_model(plan: EdPlan) -> list[_ValidationPlanCourse]:
    return [
        _ValidationPlanCourse(
            id=plan_course.id,
            plan_id=plan_course.plan_id,
            course_id=plan_course.course_id,
            planned_term_id=plan_course.planned_term_id,
            status=plan_course.status,
            course=plan_course.course,
            planned_term=plan_course.planned_term,
        )
        for plan_course in (plan.courses or [])
        if plan_course.course is not None
    ]


def _merge_candidate_course(
    plan_courses: Sequence[_ValidationPlanCourse],
    candidate: _ValidationPlanCourse,
    *,
    operation: str,
) -> list[_ValidationPlanCourse]:
    if operation == "add":
        return [*plan_courses, candidate]

    merged: list[_ValidationPlanCourse] = []
    replaced = False
    for plan_course in plan_courses:
        if plan_course.course_id == candidate.course_id:
            merged.append(
                _ValidationPlanCourse(
                    id=plan_course.id,
                    plan_id=plan_course.plan_id,
                    course_id=candidate.course_id,
                    planned_term_id=candidate.planned_term_id,
                    status=candidate.status,
                    course=candidate.course,
                    planned_term=candidate.planned_term,
                )
            )
            replaced = True
        else:
            merged.append(plan_course)
    if not replaced:
        merged.append(candidate)
    return merged


def _validate_duplicates(plan_courses: Sequence[_ValidationPlanCourse]) -> list[dict]:
    counts = Counter(plan_course.course_id for plan_course in plan_courses)
    issues = []
    for course_id, count in counts.items():
        if count <= 1:
            continue
        duplicates = [
            plan_course for plan_course in plan_courses if plan_course.course_id == course_id
        ]
        first = duplicates[0]
        issues.append(
            _issue(
                "DUPLICATE_COURSE_IN_PLAN",
                f"{first.course.course_code} appears {count} times in this plan.",
                first,
                related_courses=[duplicate.course for duplicate in duplicates[1:]],
                metadata={
                    "occurrences": count,
                    "plan_course_ids": [
                        str(plan_course.id)
                        for plan_course in duplicates
                        if plan_course.id is not None
                    ],
                },
            )
        )
    return issues


def _validate_prerequisites(
    plan_courses: Sequence[_ValidationPlanCourse],
    prerequisite_links: Sequence[CoursePrerequisite],
) -> list[dict]:
    links_by_course: dict[uuid.UUID, list[CoursePrerequisite]] = defaultdict(list)
    for link in prerequisite_links:
        links_by_course[link.course_id].append(link)

    plan_courses_by_course = _group_by_course(plan_courses)
    issues = []
    for plan_course in plan_courses:
        for link in links_by_course.get(plan_course.course_id, []):
            if _prerequisite_is_satisfied(
                plan_course,
                plan_courses_by_course.get(link.prerequisite_course_id, []),
            ):
                continue
            prerequisite_course = link.prerequisite_course
            issues.append(
                _issue(
                    "PREREQUISITE_NOT_SATISFIED",
                    (
                        f"{plan_course.course.course_code} requires "
                        f"{prerequisite_course.course_code} in an earlier term."
                    ),
                    plan_course,
                    related_courses=[prerequisite_course],
                    metadata={"prerequisite_course_id": str(link.prerequisite_course_id)},
                )
            )
    return issues


def _validate_corequisites(
    plan_courses: Sequence[_ValidationPlanCourse],
    corequisite_links: Sequence[CourseCorequisite],
) -> list[dict]:
    links_by_course: dict[uuid.UUID, list[CourseCorequisite]] = defaultdict(list)
    for link in corequisite_links:
        links_by_course[link.course_id].append(link)

    plan_courses_by_course = _group_by_course(plan_courses)
    issues = []
    for plan_course in plan_courses:
        for link in links_by_course.get(plan_course.course_id, []):
            if _corequisite_is_satisfied(
                plan_course,
                plan_courses_by_course.get(link.corequisite_course_id, []),
            ):
                continue
            corequisite_course = link.corequisite_course
            issues.append(
                _issue(
                    "COREQUISITE_NOT_SCHEDULED_SAME_TERM",
                    (
                        f"{plan_course.course.course_code} requires "
                        f"{corequisite_course.course_code} in the same term."
                    ),
                    plan_course,
                    related_courses=[corequisite_course],
                    metadata={"corequisite_course_id": str(link.corequisite_course_id)},
                )
            )
    return issues


def _validate_credits(plan_courses: Sequence[_ValidationPlanCourse]) -> list[dict]:
    courses_by_term: dict[uuid.UUID, list[_ValidationPlanCourse]] = defaultdict(list)
    for plan_course in plan_courses:
        if plan_course.planned_term_id is not None:
            courses_by_term[plan_course.planned_term_id].append(plan_course)

    issues = []
    for term_courses in courses_by_term.values():
        total = sum(plan_course.course.credits for plan_course in term_courses)
        if total <= MAX_TERM_CREDITS:
            continue
        first = term_courses[0]
        issues.append(
            _issue(
                "TERM_CREDIT_LIMIT_EXCEEDED",
                (
                    f"{_term_name(first)} has {total} planned credits, "
                    f"which exceeds the {MAX_TERM_CREDITS}-credit limit."
                ),
                first,
                related_courses=[plan_course.course for plan_course in term_courses],
                metadata={
                    "term_credits": total,
                    "max_term_credits": MAX_TERM_CREDITS,
                    "over_by": total - MAX_TERM_CREDITS,
                },
            )
        )
    return issues


def _prerequisite_is_satisfied(
    dependent: _ValidationPlanCourse,
    possible_prerequisites: Sequence[_ValidationPlanCourse],
) -> bool:
    dependent_start = _term_start(dependent)
    if dependent_start is None:
        return False

    for prerequisite in possible_prerequisites:
        prerequisite_end = _term_end(prerequisite)
        if prerequisite_end is not None and prerequisite_end < dependent_start:
            return True
    return False


def _corequisite_is_satisfied(
    course: _ValidationPlanCourse,
    possible_corequisites: Sequence[_ValidationPlanCourse],
) -> bool:
    if course.planned_term_id is None:
        return False
    return any(
        corequisite.planned_term_id is not None
        and corequisite.planned_term_id == course.planned_term_id
        for corequisite in possible_corequisites
    )


def _group_by_course(
    plan_courses: Sequence[_ValidationPlanCourse],
) -> dict[uuid.UUID, list[_ValidationPlanCourse]]:
    grouped: dict[uuid.UUID, list[_ValidationPlanCourse]] = defaultdict(list)
    for plan_course in plan_courses:
        grouped[plan_course.course_id].append(plan_course)
    return grouped


def _term_start(plan_course: _ValidationPlanCourse) -> date | None:
    return plan_course.planned_term.start_date if plan_course.planned_term else None


def _term_end(plan_course: _ValidationPlanCourse) -> date | None:
    return plan_course.planned_term.end_date if plan_course.planned_term else None


def _term_name(plan_course: _ValidationPlanCourse) -> str:
    return plan_course.planned_term.term_name if plan_course.planned_term else "Unscheduled term"


def _issue(
    code: str,
    message: str,
    plan_course: _ValidationPlanCourse,
    *,
    related_courses: Sequence[Course] | None = None,
    metadata: dict | None = None,
) -> dict:
    related_courses = related_courses or []
    return {
        "severity": "error",
        "code": code,
        "message": message,
        "plan_course_id": str(plan_course.id) if plan_course.id else None,
        "course_id": str(plan_course.course_id),
        "course_code": plan_course.course.course_code,
        "planned_term_id": (
            str(plan_course.planned_term_id) if plan_course.planned_term_id else None
        ),
        "planned_term_name": _term_name(plan_course) if plan_course.planned_term_id else None,
        "related_course_ids": [str(course.course_id) for course in related_courses],
        "related_course_codes": [course.course_code for course in related_courses],
        "metadata": metadata or {},
    }


def _validation_result(plan_id: uuid.UUID, issues: list[dict]) -> dict:
    error_count = sum(1 for issue in issues if issue["severity"] == "error")
    warning_count = sum(1 for issue in issues if issue["severity"] == "warning")
    recommendation_count = sum(1 for issue in issues if issue["severity"] == "recommendation")
    return {
        "plan_id": str(plan_id),
        "is_valid": error_count == 0,
        "issues": issues,
        "summary": {
            "error_count": error_count,
            "warning_count": warning_count,
            "recommendation_count": recommendation_count,
        },
    }


planning_validation_service = PlanningValidationService()
