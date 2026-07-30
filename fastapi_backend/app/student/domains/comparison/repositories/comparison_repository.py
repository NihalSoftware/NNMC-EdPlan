from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import bindparam, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.shared.constants.institution import NORTHERN_NEW_MEXICO_COLLEGE_NAME
from app.student.domains.discovery.models import Course, Program, University


class ComparisonRepository:
    async def search_universities(
        self,
        db: AsyncSession,
        *,
        state: str | None = None,
        city: str | None = None,
        name: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        statement = _university_query()
        if state:
            statement = statement.where(University.state.ilike(state.strip()))
        if city:
            statement = statement.where(University.city.ilike(city.strip()))
        if name:
            term = f"%{name.strip()}%"
            statement = statement.where(University.university_name.ilike(term))

        result = await db.execute(statement.order_by(University.university_name).limit(limit))
        return [
            _university_to_dict(university, include_programs=True)
            for university in result.scalars().all()
        ]

    async def get_universities_by_ids(
        self,
        db: AsyncSession,
        university_ids: list[str | uuid.UUID],
    ) -> list[dict]:
        parsed_ids = [_parse_uuid(value) for value in university_ids]
        parsed_ids = [value for value in parsed_ids if value is not None]
        if not parsed_ids:
            return []

        result = await db.execute(
            _university_query().where(University.university_id.in_(parsed_ids))
        )
        universities = {
            university.university_id: _university_to_dict(university, include_programs=True)
            for university in result.scalars().all()
        }
        return [universities[value] for value in parsed_ids if value in universities]

    async def search_programs(
        self,
        db: AsyncSession,
        *,
        university_id: str | uuid.UUID | None = None,
        degree: str | None = None,
        name: str | None = None,
        limit: int = 20,
    ) -> list[dict]:
        statement = _program_query(include_courses=False)
        if university_id:
            parsed_university_id = _parse_uuid(university_id)
            if parsed_university_id is None:
                return []
            statement = statement.where(Program.university_id == parsed_university_id)
        if degree:
            statement = statement.where(Program.degree.ilike(degree.strip()))
        if name:
            term = f"%{name.strip()}%"
            statement = statement.where(Program.program_name.ilike(term))

        result = await db.execute(statement.order_by(Program.program_name).limit(limit))
        return [
            _program_to_dict(program, include_courses=False) for program in result.scalars().all()
        ]

    async def get_programs_by_ids(
        self,
        db: AsyncSession,
        program_ids: list[str | uuid.UUID],
    ) -> list[dict]:
        parsed_ids = [_parse_uuid(value) for value in program_ids]
        parsed_ids = [value for value in parsed_ids if value is not None]
        if not parsed_ids:
            return []

        result = await db.execute(
            _program_query(include_courses=True).where(Program.program_id.in_(parsed_ids))
        )
        programs = {
            program.program_id: _program_to_dict(program, include_courses=True)
            for program in result.scalars().all()
        }
        return [programs[value] for value in parsed_ids if value in programs]

    async def get_careers_for_programs(
        self,
        db: AsyncSession,
        program_ids: list[str | uuid.UUID],
    ) -> dict[str, list[dict]]:
        parsed_ids = [_parse_uuid(value) for value in program_ids]
        parsed_ids = [value for value in parsed_ids if value is not None]
        if not parsed_ids:
            return {}

        if not await _table_exists(db, "careers"):
            return {}

        careers_by_program: dict[str, dict[str, dict]] = {
            str(program_id): {} for program_id in parsed_ids
        }
        if await _table_exists(db, "program_careers"):
            await self._add_program_careers(db, parsed_ids, careers_by_program)
        if await _table_exists(db, "course_careers"):
            await self._add_course_careers(db, parsed_ids, careers_by_program)

        return {
            program_id: sorted(careers.values(), key=lambda career: career["career_name"])
            for program_id, careers in careers_by_program.items()
        }

    async def _add_program_careers(
        self,
        db: AsyncSession,
        program_ids: list[uuid.UUID],
        careers_by_program: dict[str, dict[str, dict]],
    ) -> None:
        result = await db.execute(
            text("""
                SELECT pc.program_id, c.career_id, c.career_name, c.description
                FROM program_careers pc
                JOIN careers c ON c.career_id = pc.career_id
                WHERE pc.program_id IN :program_ids
                """).bindparams(bindparam("program_ids", expanding=True)),
            {"program_ids": program_ids},
        )
        for row in result.mappings().all():
            _add_career(careers_by_program, row, source="program_careers")

    async def _add_course_careers(
        self,
        db: AsyncSession,
        program_ids: list[uuid.UUID],
        careers_by_program: dict[str, dict[str, dict]],
    ) -> None:
        result = await db.execute(
            text("""
                SELECT co.program_id, cc.course_id, c.career_id, c.career_name, c.description
                FROM course_careers cc
                JOIN careers c ON c.career_id = cc.career_id
                JOIN courses co ON co.course_id = cc.course_id
                WHERE co.program_id IN :program_ids
                """).bindparams(bindparam("program_ids", expanding=True)),
            {"program_ids": program_ids},
        )
        for row in result.mappings().all():
            _add_career(careers_by_program, row, source="course_careers")


def _university_query():
    return (
        select(University)
        .options(selectinload(University.programs))
        .where(University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME))
    )


def _program_query(*, include_courses: bool):
    options = [selectinload(Program.university)]
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


async def _table_exists(db: AsyncSession, table_name: str) -> bool:
    try:
        result = await db.execute(
            text("""
                SELECT 1
                FROM information_schema.tables
                WHERE table_name = :table_name
                LIMIT 1
                """),
            {"table_name": table_name},
        )
    except SQLAlchemyError:
        return False
    return result.scalar_one_or_none() is not None


def _university_to_dict(university: University, *, include_programs: bool = False) -> dict:
    current_programs = [
        program
        for program in university.programs or []
        if (program.metadata_json or {}).get("is_current_catalog") is not False
    ]
    payload = {
        "university_id": str(university.university_id),
        "university_name": university.university_name,
        "name": university.university_name,
        "location": {"city": university.city, "state": university.state},
        "city": university.city,
        "state": university.state,
        "website": university.website,
        "public_private": None,
        "catalog": {
            "has_programs": bool(current_programs),
            "program_count": len(current_programs),
        },
    }
    if include_programs:
        payload["available_programs"] = [
            _program_summary_to_dict(program)
            for program in sorted(
                current_programs,
                key=lambda item: (item.program_name, item.degree),
            )
        ]
        payload["program_count"] = len(payload["available_programs"])
    return payload


def _program_to_dict(program: Program, *, include_courses: bool = False) -> dict:
    metadata = program.metadata_json or {}
    payload = _program_summary_to_dict(program)
    payload["university"] = {
        "university_id": str(program.university.university_id),
        "university_name": program.university.university_name,
        "city": program.university.city,
        "state": program.university.state,
        "website": program.university.website,
    }
    payload["duration"] = None
    payload["description"] = "\n\n".join(metadata.get("catalog_intro") or []) or None
    payload["catalog_url"] = metadata.get("catalog_url")
    payload["catalog_year"] = metadata.get("catalog_year")
    if include_courses:
        courses = sorted(
            [
                course
                for course in program.courses or []
                if (course.metadata_json or {}).get("is_current_catalog") is not False
            ],
            key=lambda course: (
                course.recommended_year or 99,
                course.recommended_semester or "",
                course.course_code,
            ),
        )
        payload["required_courses"] = [_course_to_dict(course) for course in courses]
        payload["course_count"] = len(courses)
    return payload


def _program_summary_to_dict(program: Program) -> dict:
    metadata = program.metadata_json or {}
    return {
        "program_id": str(program.program_id),
        "program_name": program.program_name,
        "degree": program.degree,
        "total_credit_hours": program.total_credit_hours,
        "catalog_title": metadata.get("catalog_title"),
        "catalog_url": metadata.get("catalog_url"),
        "catalog_year": metadata.get("catalog_year"),
    }


def _course_to_dict(course: Course) -> dict:
    metadata = course.metadata_json or {}
    return {
        "course_id": str(course.course_id),
        "course_code": course.course_code,
        "course_name": course.course_name,
        "credits": course.credits,
        "recommended_year": course.recommended_year,
        "recommended_semester": course.recommended_semester,
        "description": course.description,
        "catalog_url": metadata.get("catalog_url"),
        "credit_text": metadata.get("catalog_credit_text"),
        "metadata_json": metadata,
    }


def _add_career(
    careers_by_program: dict[str, dict[str, dict]],
    row: Any,
    *,
    source: str,
) -> None:
    program_id = str(row["program_id"])
    career_id = str(row["career_id"])
    career = careers_by_program.setdefault(program_id, {}).setdefault(
        career_id,
        {
            "career_id": career_id,
            "career_name": row["career_name"],
            "description": row.get("description"),
            "sources": [],
            "course_ids": [],
        },
    )
    if source not in career["sources"]:
        career["sources"].append(source)
    course_id = row.get("course_id")
    if course_id is not None and str(course_id) not in career["course_ids"]:
        career["course_ids"].append(str(course_id))


comparison_repository = ComparisonRepository()
