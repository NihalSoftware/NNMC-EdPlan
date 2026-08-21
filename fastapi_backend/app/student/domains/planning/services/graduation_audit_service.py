from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.student.domains.discovery.models import Course
from app.student.domains.planning.models import EdPlan, PlanCourse
from app.student.domains.planning.repositories.graduation_audit_repository import (
    GraduationAuditRepository,
    graduation_audit_repository,
)


def _parse_uuid(value: str, field_name: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}",
        ) from exc


class GraduationAuditService:
    def __init__(
        self,
        repository: GraduationAuditRepository | None = None,
    ) -> None:
        self.repository = repository or graduation_audit_repository

    async def get_audit(
        self,
        db: AsyncSession,
        plan_id: str,
        *,
        expected_user_id: int | None = None,
    ) -> dict:
        parsed_plan_id = _parse_uuid(plan_id, "plan_id")
        plan = await self.repository.get_plan(db, parsed_plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        if expected_user_id is not None and plan.user_id != expected_user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
        if not plan.program:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")

        catalog_courses = await self.repository.list_program_courses(db, plan.program_id)
        return _build_audit(plan, catalog_courses)


def _build_audit(plan: EdPlan, catalog_courses: list[Course]) -> dict:
    plan_courses = list(plan.courses or [])
    planned_credits = _planned_credits(plan_courses)
    required_credits = plan.program.total_credit_hours
    remaining_credits = max(required_credits - planned_credits, 0)

    program_course_ids = {course.course_id for course in catalog_courses}
    planned_course_ids = {
        plan_course.course_id
        for plan_course in plan_courses
        if plan_course.course_id in program_course_ids
    }
    missing_courses = [
        course for course in catalog_courses if course.course_id not in planned_course_ids
    ]

    total_required_courses = len(catalog_courses)
    completed_course_count = len(planned_course_ids)
    missing_course_count = len(missing_courses)

    return {
        "plan_id": str(plan.plan_id),
        "program": {
            "program_id": str(plan.program.program_id),
            "program_name": plan.program.program_name,
            "degree": plan.program.degree,
            "required_credits": required_credits,
        },
        "credits": {
            "planned": planned_credits,
            "required": required_credits,
            "remaining": remaining_credits,
            "completion_percentage": _percentage(planned_credits, required_credits),
        },
        "courses": {
            "total_required": total_required_courses,
            "completed": completed_course_count,
            "missing": missing_course_count,
            "completion_percentage": _percentage(
                completed_course_count,
                total_required_courses,
            ),
        },
        "graduation_ready": missing_course_count == 0 and planned_credits >= required_credits,
        "missing_courses": [_course_to_dict(course) for course in missing_courses],
    }


def _planned_credits(plan_courses: list[PlanCourse]) -> float:
    return sum(
        (
            float(plan_course.course.credits)
            for plan_course in plan_courses
            if plan_course.course is not None
        ),
        0.0,
    )


def _percentage(numerator: float | int, denominator: float | int) -> float:
    if denominator <= 0:
        return 0.0
    return min(round((numerator / denominator) * 100, 2), 100.0)


def _course_to_dict(course: Course) -> dict:
    return {
        "course_id": str(course.course_id),
        "course_code": course.course_code,
        "course_name": course.course_name,
    }


graduation_audit_service = GraduationAuditService()
