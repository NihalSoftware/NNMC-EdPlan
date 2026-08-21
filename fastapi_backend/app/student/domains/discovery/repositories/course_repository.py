from __future__ import annotations

import uuid

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.shared.constants.institution import NORTHERN_NEW_MEXICO_COLLEGE_NAME
from app.student.domains.discovery.models import (
    Course,
    CourseCorequisite,
    CoursePrerequisite,
    Program,
    University,
)


class CourseRepository:
    async def list_courses(
        self,
        db: AsyncSession,
        *,
        program_id: str | uuid.UUID | None = None,
        search: str | None = None,
    ) -> list[dict]:
        statement = _course_query()
        if program_id:
            parsed_program_id = _parse_uuid(program_id)
            if parsed_program_id is None:
                return []
            statement = statement.where(Course.program_id == parsed_program_id)
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Course.course_code.ilike(term),
                    Course.course_name.ilike(term),
                    Course.description.ilike(term),
                )
            )

        statement = statement.order_by(
            Course.recommended_year,
            Course.recommended_semester,
            Course.course_code,
        )
        result = await db.execute(statement)
        return [_course_to_dict(course) for course in result.scalars().all()]

    async def get_course_by_id(self, db: AsyncSession, course_id: str | uuid.UUID) -> dict | None:
        parsed_course_id = _parse_uuid(course_id)
        if parsed_course_id is None:
            return None
        result = await db.execute(
            _course_query(include_dependencies=True).where(Course.course_id == parsed_course_id)
        )
        course = result.scalar_one_or_none()
        return _course_to_dict(course, include_dependencies=True) if course else None

    async def list_prerequisites(
        self, db: AsyncSession, course_id: str | uuid.UUID
    ) -> list[dict] | None:
        parsed_course_id = _parse_uuid(course_id)
        if parsed_course_id is None:
            return None
        result = await db.execute(
            select(CoursePrerequisite)
            .options(joinedload(CoursePrerequisite.prerequisite_course))
            .where(
                CoursePrerequisite.course_id == parsed_course_id,
                CoursePrerequisite.course.has(
                    and_(
                        Course.metadata_json["is_current_catalog"].as_boolean().is_not(False),
                        Course.program.has(
                            and_(
                                Program.metadata_json["is_current_catalog"]
                                .as_boolean()
                                .is_not(False),
                                Program.university.has(
                                    University.university_name.ilike(
                                        NORTHERN_NEW_MEXICO_COLLEGE_NAME
                                    )
                                ),
                            )
                        ),
                    )
                ),
            )
        )
        return [_prerequisite_to_dict(link) for link in result.scalars().all()]

    async def list_corequisites(
        self, db: AsyncSession, course_id: str | uuid.UUID
    ) -> list[dict] | None:
        parsed_course_id = _parse_uuid(course_id)
        if parsed_course_id is None:
            return None
        result = await db.execute(
            select(CourseCorequisite)
            .options(joinedload(CourseCorequisite.corequisite_course))
            .where(
                CourseCorequisite.course_id == parsed_course_id,
                CourseCorequisite.course.has(
                    and_(
                        Course.metadata_json["is_current_catalog"].as_boolean().is_not(False),
                        Course.program.has(
                            and_(
                                Program.metadata_json["is_current_catalog"]
                                .as_boolean()
                                .is_not(False),
                                Program.university.has(
                                    University.university_name.ilike(
                                        NORTHERN_NEW_MEXICO_COLLEGE_NAME
                                    )
                                ),
                            )
                        ),
                    )
                ),
            )
        )
        return [_corequisite_to_dict(link) for link in result.scalars().all()]


def _course_query(*, include_dependencies: bool = False):
    options = [joinedload(Course.program).joinedload(Program.university)]
    if include_dependencies:
        options.extend(
            [
                selectinload(Course.prerequisite_links).joinedload(
                    CoursePrerequisite.prerequisite_course
                ),
                selectinload(Course.corequisite_links).joinedload(
                    CourseCorequisite.corequisite_course
                ),
            ]
        )
    return (
        select(Course)
        .options(*options)
        .where(
            Course.metadata_json["is_current_catalog"].as_boolean().is_not(False),
            Course.program.has(
                and_(
                    Program.metadata_json["is_current_catalog"].as_boolean().is_not(False),
                    Program.university.has(
                        University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
                    ),
                )
            ),
        )
    )


def _parse_uuid(value: str | uuid.UUID) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _course_to_dict(course: Course, *, include_dependencies: bool = False) -> dict:
    payload = _course_summary_to_dict(course)
    program = course.program
    program_metadata = program.metadata_json or {}
    payload["program"] = {
        "program_id": str(program.program_id),
        "program_name": program.program_name,
        "degree": program.degree,
        "total_credit_hours": program.total_credit_hours,
        "total_credit_hours_text": program_metadata.get("catalog_total_credits_text"),
        "total_credit_hours_min": program_metadata.get("catalog_total_credits_min"),
        "total_credit_hours_max": program_metadata.get("catalog_total_credits_max"),
        "catalog_title": program_metadata.get("catalog_title"),
        "catalog_url": program_metadata.get("catalog_url"),
        "catalog_year": program_metadata.get("catalog_year"),
        "description": "\n\n".join(program_metadata.get("catalog_intro") or []) or None,
        "metadata_json": program_metadata,
        "official_source_id": program.official_source_id,
        "official_source_url": program.official_source_url,
        "source_retrieved_at": program.source_retrieved_at,
        "university": {
            "university_id": str(program.university.university_id),
            "university_name": program.university.university_name,
            "city": program.university.city,
            "state": program.university.state,
            "website": program.university.website,
        },
    }
    if include_dependencies:
        payload["prerequisites"] = [
            _prerequisite_to_dict(link) for link in course.prerequisite_links
        ]
        payload["corequisites"] = [_corequisite_to_dict(link) for link in course.corequisite_links]
    return payload


def _course_summary_to_dict(course: Course) -> dict:
    metadata = course.metadata_json or {}
    return {
        "course_id": str(course.course_id),
        "program_id": str(course.program_id),
        "course_code": course.course_code,
        "code": course.course_code,
        "course_name": course.course_name,
        "name": course.course_name,
        "credits": course.credits,
        "lecture_hours": course.lecture_hours,
        "lab_hours": course.lab_hours,
        "recommended_year": course.recommended_year,
        "year": course.recommended_year,
        "recommended_semester": course.recommended_semester,
        "semester": course.recommended_semester,
        "is_elective": course.is_elective,
        "default_plan_eligible": course.default_plan_eligible,
        "prerequisite": metadata.get("prerequisite"),
        "corequisite": metadata.get("corequisite"),
        "pre_or_corequisite": metadata.get("pre_or_corequisite"),
        "requirement_expressions": metadata.get("requirement_expressions") or {},
        "description": course.description,
        "metadata_json": metadata,
        "source_sequence": course.source_sequence,
        "catalog_url": metadata.get("catalog_url"),
        "credit_text": metadata.get("catalog_credit_text"),
        "credits_min": metadata.get("credits_min"),
        "credits_max": metadata.get("credits_max"),
        "requirement_occurrences": metadata.get("requirement_occurrences") or [],
        "official_source_id": course.official_source_id,
        "official_source_url": course.official_source_url,
        "source_retrieved_at": course.source_retrieved_at,
    }


def _prerequisite_to_dict(link: CoursePrerequisite) -> dict:
    return {
        "id": str(link.id),
        "course_id": str(link.course_id),
        "prerequisite_course_id": str(link.prerequisite_course_id),
        "course": _course_summary_to_dict(link.prerequisite_course),
    }


def _corequisite_to_dict(link: CourseCorequisite) -> dict:
    return {
        "id": str(link.id),
        "course_id": str(link.course_id),
        "corequisite_course_id": str(link.corequisite_course_id),
        "course": _course_summary_to_dict(link.corequisite_course),
    }


course_repository = CourseRepository()
