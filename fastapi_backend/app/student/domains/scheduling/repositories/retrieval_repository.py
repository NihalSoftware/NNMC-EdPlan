from __future__ import annotations

import uuid
from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.shared.constants.institution import NORTHERN_NEW_MEXICO_COLLEGE_NAME
from app.student.domains.discovery.models import University
from app.student.domains.planning.models import EdPlan, PlanCourse
from app.student.domains.scheduling.models import (
    AcademicTerm,
    CourseOffering,
    Section,
    SectionMeeting,
)


class ScheduleRetrievalRepository:
    """Read-only batch repository for SchedulePilot retrieval workloads."""

    async def get_student_plan(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        plan_id: str | uuid.UUID,
    ) -> EdPlan | None:
        parsed_plan_id = _parse_uuid(plan_id)
        if parsed_plan_id is None:
            return None
        result = await db.execute(
            select(EdPlan)
            .options(
                joinedload(EdPlan.university),
                joinedload(EdPlan.program),
            )
            .where(
                EdPlan.plan_id == parsed_plan_id,
                EdPlan.user_id == user_id,
                EdPlan.university.has(
                    University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
                ),
            )
        )
        return result.scalar_one_or_none()

    async def get_plan_courses(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
    ) -> list[PlanCourse] | None:
        parsed_plan_id = _parse_uuid(plan_id)
        if parsed_plan_id is None:
            return None
        result = await db.execute(
            select(PlanCourse)
            .options(
                joinedload(PlanCourse.course),
                joinedload(PlanCourse.planned_term),
            )
            .where(PlanCourse.plan_id == parsed_plan_id)
            .join(PlanCourse.course)
            .outerjoin(PlanCourse.planned_term)
            .order_by(AcademicTerm.start_date, PlanCourse.status)
        )
        return list(result.scalars().all())

    async def get_active_terms(self, db: AsyncSession) -> list[AcademicTerm]:
        result = await db.execute(
            select(AcademicTerm)
            .where(AcademicTerm.is_active.is_(True))
            .order_by(AcademicTerm.start_date, AcademicTerm.term_name)
        )
        return list(result.scalars().all())

    async def get_offerings_for_courses(
        self,
        db: AsyncSession,
        *,
        course_ids: Iterable[str | uuid.UUID],
    ) -> list[CourseOffering]:
        parsed_course_ids = _parse_uuid_list(course_ids)
        if not parsed_course_ids:
            return []
        result = await db.execute(
            select(CourseOffering)
            .options(
                joinedload(CourseOffering.course),
                joinedload(CourseOffering.term),
            )
            .join(CourseOffering.term)
            .where(CourseOffering.course_id.in_(parsed_course_ids))
            .order_by(AcademicTerm.start_date, CourseOffering.offering_type)
        )
        return list(result.scalars().all())

    async def get_sections_for_offerings(
        self,
        db: AsyncSession,
        *,
        offering_ids: Iterable[str | uuid.UUID],
        status: str = "Open",
    ) -> list[Section]:
        parsed_offering_ids = _parse_uuid_list(offering_ids)
        if not parsed_offering_ids:
            return []
        result = await db.execute(
            select(Section)
            .options(
                joinedload(Section.offering).joinedload(CourseOffering.term),
                joinedload(Section.offering).joinedload(CourseOffering.course),
            )
            .where(Section.offering_id.in_(parsed_offering_ids), Section.status == status)
            .order_by(Section.offering_id, Section.section_number)
        )
        return list(result.scalars().all())

    async def get_meetings_for_sections(
        self,
        db: AsyncSession,
        *,
        section_ids: Iterable[str | uuid.UUID],
    ) -> list[SectionMeeting]:
        parsed_section_ids = _parse_uuid_list(section_ids)
        if not parsed_section_ids:
            return []
        result = await db.execute(
            select(SectionMeeting)
            .options(selectinload(SectionMeeting.section))
            .where(SectionMeeting.section_id.in_(parsed_section_ids))
            .order_by(
                SectionMeeting.section_id,
                SectionMeeting.weekday,
                SectionMeeting.start_time,
                SectionMeeting.meeting_type,
            )
        )
        return list(result.scalars().all())


def _parse_uuid(value: str | uuid.UUID) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _parse_uuid_list(values: Iterable[str | uuid.UUID]) -> list[uuid.UUID]:
    parsed_values: list[uuid.UUID] = []
    for value in values:
        parsed = _parse_uuid(value)
        if parsed is not None and parsed not in parsed_values:
            parsed_values.append(parsed)
    return parsed_values


schedule_retrieval_repository = ScheduleRetrievalRepository()
