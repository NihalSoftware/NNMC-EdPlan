from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.shared.constants.institution import NORTHERN_NEW_MEXICO_COLLEGE_NAME
from app.student.domains.discovery.models import Course, Program, University
from app.student.domains.scheduling.models import (
    AcademicTerm,
    CourseOffering,
    Section,
    SectionMeeting,
)


class TermRepository:
    async def list_terms(self, db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(AcademicTerm).order_by(AcademicTerm.start_date, AcademicTerm.term_name)
        )
        return [_term_to_dict(term) for term in result.scalars().all()]

    async def get_term_by_id(self, db: AsyncSession, term_id: str | uuid.UUID) -> dict | None:
        parsed_term_id = _parse_uuid(term_id)
        if parsed_term_id is None:
            return None
        result = await db.execute(
            select(AcademicTerm).where(AcademicTerm.term_id == parsed_term_id)
        )
        term = result.scalar_one_or_none()
        return _term_to_dict(term) if term else None


class CourseOfferingRepository:
    async def list_offerings_by_course(
        self, db: AsyncSession, course_id: str | uuid.UUID
    ) -> list[dict] | None:
        parsed_course_id = _parse_uuid(course_id)
        if parsed_course_id is None:
            return None
        result = await db.execute(
            _offering_query()
            .join(CourseOffering.term)
            .where(CourseOffering.course_id == parsed_course_id)
            .order_by(AcademicTerm.start_date, CourseOffering.offering_type)
        )
        return [_offering_to_dict(offering) for offering in result.scalars().all()]

    async def get_offering_by_id(
        self, db: AsyncSession, offering_id: str | uuid.UUID
    ) -> dict | None:
        parsed_offering_id = _parse_uuid(offering_id)
        if parsed_offering_id is None:
            return None
        result = await db.execute(
            _offering_query().where(CourseOffering.offering_id == parsed_offering_id)
        )
        offering = result.scalar_one_or_none()
        return _offering_to_dict(offering) if offering else None


class SectionRepository:
    async def list_sections_by_offering(
        self, db: AsyncSession, offering_id: str | uuid.UUID
    ) -> list[dict] | None:
        parsed_offering_id = _parse_uuid(offering_id)
        if parsed_offering_id is None:
            return None
        result = await db.execute(
            _section_query()
            .where(Section.offering_id == parsed_offering_id)
            .order_by(Section.section_number)
        )
        return [_section_to_dict(section) for section in result.scalars().all()]

    async def get_section_by_id(self, db: AsyncSession, section_id: str | uuid.UUID) -> dict | None:
        parsed_section_id = _parse_uuid(section_id)
        if parsed_section_id is None:
            return None
        result = await db.execute(_section_query().where(Section.section_id == parsed_section_id))
        section = result.scalar_one_or_none()
        return _section_to_dict(section, include_offering=True) if section else None


class SectionMeetingRepository:
    async def list_meetings_by_section(
        self, db: AsyncSession, section_id: str | uuid.UUID
    ) -> list[dict] | None:
        parsed_section_id = _parse_uuid(section_id)
        if parsed_section_id is None:
            return None
        result = await db.execute(
            select(SectionMeeting)
            .where(
                SectionMeeting.section_id == parsed_section_id,
                SectionMeeting.section.has(
                    Section.offering.has(
                        CourseOffering.course.has(
                            Course.program.has(
                                Program.university.has(
                                    University.university_name.ilike(
                                        NORTHERN_NEW_MEXICO_COLLEGE_NAME
                                    )
                                )
                            )
                        )
                    )
                ),
            )
            .order_by(
                SectionMeeting.weekday,
                SectionMeeting.start_time,
                SectionMeeting.meeting_type,
            )
        )
        return [_meeting_to_dict(meeting) for meeting in result.scalars().all()]


def _offering_query():
    return (
        select(CourseOffering)
        .options(
            joinedload(CourseOffering.course),
            joinedload(CourseOffering.term),
        )
        .where(
            CourseOffering.course.has(
                Course.program.has(
                    Program.university.has(
                        University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
                    )
                )
            )
        )
    )


def _section_query():
    return (
        select(Section)
        .options(
            joinedload(Section.offering).joinedload(CourseOffering.term),
            joinedload(Section.offering).joinedload(CourseOffering.course),
        )
        .where(
            Section.offering.has(
                CourseOffering.course.has(
                    Course.program.has(
                        Program.university.has(
                            University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
                        )
                    )
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


def _term_to_dict(term: AcademicTerm) -> dict:
    return {
        "term_id": str(term.term_id),
        "term_name": term.term_name,
        "start_date": term.start_date,
        "end_date": term.end_date,
        "is_active": term.is_active,
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


def _offering_to_dict(offering: CourseOffering) -> dict:
    return {
        "offering_id": str(offering.offering_id),
        "course_id": str(offering.course_id),
        "term_id": str(offering.term_id),
        "offering_type": offering.offering_type,
        "course": _course_to_dict(offering.course),
        "term": _term_to_dict(offering.term),
    }


def _section_to_dict(section: Section, *, include_offering: bool = False) -> dict:
    payload: dict[str, Any] = {
        "section_id": str(section.section_id),
        "offering_id": str(section.offering_id),
        "section_number": section.section_number,
        "crn": section.crn,
        "campus": section.campus,
        "instructor": section.instructor,
        "instruction_method": section.instruction_method,
        "capacity": section.capacity,
        "enrolled": section.enrolled,
        "status": section.status,
    }
    if include_offering:
        payload["offering"] = _offering_to_dict(section.offering)
    return payload


def _meeting_to_dict(meeting: SectionMeeting) -> dict:
    return {
        "meeting_id": str(meeting.meeting_id),
        "section_id": str(meeting.section_id),
        "weekday": meeting.weekday,
        "start_time": meeting.start_time,
        "end_time": meeting.end_time,
        "building": meeting.building,
        "room": meeting.room,
        "meeting_type": meeting.meeting_type,
    }


term_repository = TermRepository()
offering_repository = CourseOfferingRepository()
section_repository = SectionRepository()
section_meeting_repository = SectionMeetingRepository()
