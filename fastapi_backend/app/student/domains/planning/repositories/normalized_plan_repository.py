from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

# Initialize Base metadata before importing model packages from a cold route import.
from app.db.base import Base as _Base  # noqa: F401
from app.shared.constants.institution import NORTHERN_NEW_MEXICO_COLLEGE_NAME
from app.student.domains.discovery.models import Course, Program, University
from app.student.domains.planning.models import EdPlan, PlanCourse
from app.student.domains.scheduling.models import AcademicTerm


class NormalizedPlanRepository:
    async def list_plans(
        self,
        db: AsyncSession,
        *,
        user_id: int | None = None,
        is_active: bool | None = None,
    ) -> list[dict]:
        statement = _plan_query(include_courses=True)
        if user_id is not None:
            statement = statement.where(EdPlan.user_id == user_id)
        if is_active is not None:
            statement = statement.where(EdPlan.is_active == is_active)
        result = await db.execute(statement.order_by(EdPlan.created_at.desc()))
        return [_plan_to_dict(plan, include_courses=True) for plan in result.scalars().all()]

    async def get_plan_by_id(self, db: AsyncSession, plan_id: str | uuid.UUID) -> dict | None:
        plan = await self.get_plan_model(db, plan_id, include_courses=True)
        return _plan_to_dict(plan, include_courses=True) if plan else None

    async def get_plan_model(
        self,
        db: AsyncSession,
        plan_id: str | uuid.UUID,
        *,
        include_courses: bool = False,
    ) -> EdPlan | None:
        parsed_plan_id = _parse_uuid(plan_id)
        if parsed_plan_id is None:
            return None
        result = await db.execute(
            _plan_query(include_courses=include_courses).where(EdPlan.plan_id == parsed_plan_id)
        )
        return result.scalar_one_or_none()

    async def create_plan(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        university_id: uuid.UUID,
        program_id: uuid.UUID,
        plan_name: str,
        description: str | None,
        is_active: bool,
    ) -> EdPlan:
        selection = await db.execute(
            select(Program.program_id).where(
                Program.program_id == program_id,
                Program.university_id == university_id,
                Program.university.has(
                    University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
                ),
            )
        )
        if selection.scalar_one_or_none() is None:
            raise ValueError("Plan must use a Northern New Mexico College program.")
        plan = EdPlan(
            user_id=user_id,
            university_id=university_id,
            program_id=program_id,
            plan_name=plan_name,
            description=description,
            is_active=is_active,
        )
        db.add(plan)
        await db.flush()
        return plan

    async def update_plan(
        self,
        plan: EdPlan,
        *,
        plan_name: str | None = None,
        description: str | None = None,
        update_description: bool = False,
        is_active: bool | None = None,
    ) -> EdPlan:
        if plan_name is not None:
            plan.plan_name = plan_name
        if update_description:
            plan.description = description
        if is_active is not None:
            plan.is_active = is_active
        return plan

    async def deactivate_plan(self, plan: EdPlan) -> EdPlan:
        plan.is_active = False
        return plan


class PlanCourseRepository:
    async def list_plan_courses(
        self, db: AsyncSession, plan_id: str | uuid.UUID
    ) -> list[dict] | None:
        parsed_plan_id = _parse_uuid(plan_id)
        if parsed_plan_id is None:
            return None
        result = await db.execute(
            _plan_course_query()
            .where(PlanCourse.plan_id == parsed_plan_id)
            .order_by(AcademicTerm.start_date, Course.course_code)
        )
        courses = result.scalars().all()
        return [_plan_course_to_dict(course) for course in courses]

    async def get_plan_course_model(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
        course_id: str | uuid.UUID,
    ) -> PlanCourse | None:
        parsed_plan_id = _parse_uuid(plan_id)
        parsed_course_id = _parse_uuid(course_id)
        if parsed_plan_id is None or parsed_course_id is None:
            return None
        result = await db.execute(
            _plan_course_query()
            .where(PlanCourse.plan_id == parsed_plan_id)
            .where(PlanCourse.course_id == parsed_course_id)
        )
        return result.scalar_one_or_none()

    async def get_plan_course(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
        course_id: str | uuid.UUID,
    ) -> dict | None:
        plan_course = await self.get_plan_course_model(
            db,
            plan_id=plan_id,
            course_id=course_id,
        )
        return _plan_course_to_dict(plan_course) if plan_course else None

    async def add_plan_course(
        self,
        db: AsyncSession,
        *,
        plan_id: uuid.UUID,
        course_id: uuid.UUID,
        planned_term_id: uuid.UUID | None,
        status: str,
        notes: str | None,
    ) -> PlanCourse:
        plan_course = PlanCourse(
            plan_id=plan_id,
            course_id=course_id,
            planned_term_id=planned_term_id,
            status=status,
            notes=notes,
        )
        db.add(plan_course)
        await db.flush()
        return plan_course

    async def update_plan_course(
        self,
        plan_course: PlanCourse,
        *,
        planned_term_id: uuid.UUID | None = None,
        update_planned_term: bool = False,
        status: str | None = None,
        notes: str | None = None,
        update_notes: bool = False,
    ) -> PlanCourse:
        if update_planned_term:
            plan_course.planned_term_id = planned_term_id
        if status is not None:
            plan_course.status = status
        if update_notes:
            plan_course.notes = notes
        return plan_course

    async def delete_plan_course(self, db: AsyncSession, plan_course: PlanCourse) -> None:
        await db.delete(plan_course)


def _plan_query(*, include_courses: bool = False):
    options = [
        joinedload(EdPlan.university),
        joinedload(EdPlan.program).joinedload(Program.university),
    ]
    if include_courses:
        options.append(
            selectinload(EdPlan.courses)
            .joinedload(PlanCourse.course)
            .joinedload(Course.program)
            .joinedload(Program.university)
        )
        options.append(selectinload(EdPlan.courses).joinedload(PlanCourse.planned_term))
    return (
        select(EdPlan)
        .options(*options)
        .where(
            EdPlan.university.has(
                University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
            )
        )
    )


def _plan_course_query():
    return (
        select(PlanCourse)
        .options(
            joinedload(PlanCourse.course).joinedload(Course.program).joinedload(Program.university),
            joinedload(PlanCourse.planned_term),
        )
        .outerjoin(PlanCourse.planned_term)
        .join(PlanCourse.course)
        .where(
            PlanCourse.plan.has(
                EdPlan.university.has(
                    University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
                )
            )
        )
    )


def _parse_uuid(value: str | uuid.UUID) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _plan_to_dict(plan: EdPlan, *, include_courses: bool = False) -> dict:
    courses = list(plan.courses or []) if include_courses else []
    payload = {
        "plan_id": str(plan.plan_id),
        "user_id": plan.user_id,
        "university_id": str(plan.university_id),
        "program_id": str(plan.program_id),
        "plan_name": plan.plan_name,
        "description": plan.description,
        "is_active": plan.is_active,
        "created_at": plan.created_at,
        "updated_at": plan.updated_at,
        "university": _university_to_dict(plan.university) if plan.university else None,
        "program": _program_to_dict(plan.program) if plan.program else None,
        "max_term_credits": 18,
    }
    if include_courses:
        payload["courses"] = [_plan_course_to_dict(course) for course in courses]
        payload["term_credit_totals"] = _term_credit_totals(courses)
    return payload


def _plan_course_to_dict(plan_course: PlanCourse) -> dict:
    return {
        "id": str(plan_course.id),
        "plan_id": str(plan_course.plan_id),
        "course_id": str(plan_course.course_id),
        "planned_term_id": (
            str(plan_course.planned_term_id) if plan_course.planned_term_id else None
        ),
        "status": plan_course.status,
        "notes": plan_course.notes,
        "course": _course_to_dict(plan_course.course) if plan_course.course else None,
        "planned_term": (
            _term_to_dict(plan_course.planned_term) if plan_course.planned_term else None
        ),
    }


def _term_credit_totals(plan_courses: Sequence[PlanCourse]) -> list[dict]:
    totals: dict[str | None, dict] = {}
    for plan_course in plan_courses:
        term_id = str(plan_course.planned_term_id) if plan_course.planned_term_id else None
        if term_id not in totals:
            totals[term_id] = {
                "planned_term_id": term_id,
                "term_name": (
                    plan_course.planned_term.term_name if plan_course.planned_term else None
                ),
                "credits": 0,
            }
        totals[term_id]["credits"] += plan_course.course.credits if plan_course.course else 0
    return list(totals.values())


def _university_to_dict(university: University) -> dict:
    return {
        "university_id": str(university.university_id),
        "university_name": university.university_name,
        "city": university.city,
        "state": university.state,
        "website": university.website,
    }


def _program_to_dict(program: Program) -> dict:
    return {
        "program_id": str(program.program_id),
        "program_name": program.program_name,
        "degree": program.degree,
        "total_credit_hours": program.total_credit_hours,
        "university": _university_to_dict(program.university) if program.university else None,
    }


def _course_to_dict(course: Course) -> dict:
    return {
        "course_id": str(course.course_id),
        "program_id": str(course.program_id),
        "course_code": course.course_code,
        "code": course.course_code,
        "course_name": course.course_name,
        "credits": course.credits,
        "lecture_hours": course.lecture_hours,
        "lab_hours": course.lab_hours,
        "recommended_year": course.recommended_year,
        "year": course.recommended_year,
        "recommended_semester": course.recommended_semester,
        "semester": course.recommended_semester,
        "description": course.description,
    }


def _term_to_dict(term: AcademicTerm) -> dict:
    return {
        "term_id": str(term.term_id),
        "term_name": term.term_name,
        "start_date": term.start_date,
        "end_date": term.end_date,
        "is_active": term.is_active,
    }


normalized_plan_repository = NormalizedPlanRepository()
plan_course_repository = PlanCourseRepository()
