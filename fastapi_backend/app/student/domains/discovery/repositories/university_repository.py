from __future__ import annotations

import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.constants.institution import (
    NORTHERN_NEW_MEXICO_COLLEGE_NAME,
    state_filter_aliases,
)
from app.student.domains.discovery.models import University


class UniversityRepository:
    async def list_universities(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
        state: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[dict]:
        statement = select(University).where(
            University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
        )
        if search:
            term = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    University.university_name.ilike(term),
                    University.city.ilike(term),
                    University.state.ilike(term),
                )
            )
        if state:
            aliases = state_filter_aliases(state)
            statement = statement.where(or_(*(University.state.ilike(alias) for alias in aliases)))

        statement = statement.order_by(University.university_name).offset(offset).limit(limit)
        result = await db.execute(statement)
        return [_university_to_dict(university) for university in result.scalars().all()]

    async def get_university_by_id(
        self, db: AsyncSession, university_id: str | uuid.UUID
    ) -> dict | None:
        parsed_university_id = _parse_uuid(university_id)
        if parsed_university_id is None:
            return None
        result = await db.execute(
            select(University).where(
                University.university_id == parsed_university_id,
                University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME),
            )
        )
        university = result.scalar_one_or_none()
        return _university_to_dict(university) if university else None

    async def get_universities_by_ids(
        self, db: AsyncSession, university_ids: list[str | uuid.UUID]
    ) -> list[dict]:
        parsed_ids = [_parse_uuid(value) for value in university_ids]
        parsed_ids = [value for value in parsed_ids if value is not None]
        if not parsed_ids:
            return []

        result = await db.execute(
            select(University).where(
                University.university_id.in_(parsed_ids),
                University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME),
            )
        )
        universities = {
            university.university_id: _university_to_dict(university)
            for university in result.scalars().all()
        }
        return [universities[value] for value in parsed_ids if value in universities]


def _parse_uuid(value: str | uuid.UUID) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _university_to_dict(university: University) -> dict:
    location = f"{university.city}, {university.state}"
    return {
        "university_id": str(university.university_id),
        "unit_id": str(university.university_id),
        "university_name": university.university_name,
        "name": university.university_name,
        "city": university.city,
        "state": university.state,
        "website": university.website,
        "college_info": {
            "website": university.website,
            "location": location,
        },
        "organization_type": "University",
        "location_type": None,
        "size": None,
        "graduation_rate": None,
        "average_annual_cost": None,
        "median_earnings": None,
        "financial_aid_debt": None,
        "typical_earnings": None,
        "acceptance_rate": None,
    }


university_repository = UniversityRepository()
