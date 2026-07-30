from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.shared.constants.institution import NORTHERN_NEW_MEXICO_COLLEGE_NAME
from app.student.domains.discovery.models import Course, Program, University


class ProgramRepository:
    async def get_programs(
        self,
        db: AsyncSession,
        *,
        university_id: str | uuid.UUID | None = None,
        degree: str | None = None,
        search: str | None = None,
    ) -> list[dict]:
        statement = _program_query()
        if university_id:
            parsed_university_id = _parse_uuid(university_id)
            if parsed_university_id is None:
                return []
            statement = statement.where(Program.university_id == parsed_university_id)
        if degree:
            statement = statement.where(Program.degree.ilike(degree.strip()))
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Program.program_name.ilike(term),
                    Program.degree.ilike(term),
                    Program.university.has(University.university_name.ilike(term)),
                )
            )

        result = await db.execute(statement.order_by(Program.program_name))
        return [_program_to_dict(program) for program in result.scalars().all()]

    async def get_program_by_id(self, db: AsyncSession, program_id: str) -> dict | None:
        parsed_program_id = _parse_uuid(program_id)
        if parsed_program_id is None:
            return None
        result = await db.execute(
            _program_query(include_courses=True).where(Program.program_id == parsed_program_id)
        )
        program = result.scalar_one_or_none()
        return _program_to_dict(program, include_courses=True) if program else None

    async def search_programs(self, db: AsyncSession, query: str) -> list[dict]:
        return await self.get_programs(db, search=query)

    async def get_programs_by_university(self, db: AsyncSession, university_id: str) -> list[dict]:
        return await self.get_programs(db, university_id=university_id)


def _program_query(*, include_courses: bool = False):
    options = [joinedload(Program.university)]
    if include_courses:
        options.append(selectinload(Program.courses))
    return (
        select(Program)
        .options(*options)
        .where(
            Program.metadata_json["is_current_catalog"].as_boolean().is_not(False),
            Program.university.has(
                University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
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


def _program_to_dict(program: Program, *, include_courses: bool = False) -> dict:
    university = program.university
    metadata = program.metadata_json or {}
    intro = metadata.get("catalog_intro") or []
    payload = {
        "program_id": str(program.program_id),
        "program_name": program.program_name,
        "degree": program.degree,
        "total_credit_hours": program.total_credit_hours,
        "catalog_title": metadata.get("catalog_title"),
        "catalog_url": metadata.get("catalog_url"),
        "catalog_year": metadata.get("catalog_year"),
        "description": "\n\n".join(intro) if intro else None,
        "metadata_json": metadata,
        "university": {
            "university_id": str(university.university_id),
            "university_name": university.university_name,
            "city": university.city,
            "state": university.state,
            "website": university.website,
        },
    }
    if include_courses:
        courses = sorted(
            [
                course
                for course in program.courses
                if (course.metadata_json or {}).get("is_current_catalog") is not False
            ],
            key=lambda course: (
                course.recommended_year or 99,
                course.recommended_semester or "",
                course.course_code,
            ),
        )
        payload["courses"] = [_course_summary_to_dict(course) for course in courses]
        payload["years"] = _courses_to_years(courses)
    return payload


def _course_summary_to_dict(course: Course) -> dict:
    metadata = course.metadata_json or {}
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
        "is_elective": course.is_elective,
        "default_plan_eligible": course.default_plan_eligible,
        "description": course.description,
        "prerequisite": metadata.get("prerequisite"),
        "corequisite": metadata.get("corequisite"),
        "catalog_url": metadata.get("catalog_url"),
        "credit_text": metadata.get("catalog_credit_text"),
        "credits_min": metadata.get("credits_min"),
        "credits_max": metadata.get("credits_max"),
        "requirement_occurrences": metadata.get("requirement_occurrences") or [],
        "metadata_json": metadata,
        "source_sequence": course.source_sequence,
    }


def _courses_to_years(courses: list[Course]) -> list[dict]:
    year_map: dict[str, dict[str, list[dict]]] = {}
    for course in courses:
        year = str(course.recommended_year or "Unassigned Year")
        semester = course.recommended_semester or "Unassigned Semester"
        year_map.setdefault(year, {}).setdefault(semester, []).append(
            _course_summary_to_dict(course)
        )

    return [
        {
            "year": year,
            "semesters": [
                {"semester": semester, "courses": semester_courses}
                for semester, semester_courses in semester_map.items()
            ],
        }
        for year, semester_map in year_map.items()
    ]


program_repository = ProgramRepository()
