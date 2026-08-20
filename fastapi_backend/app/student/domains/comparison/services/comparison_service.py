from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.student.domains.comparison.repositories.comparison_repository import (
    ComparisonRepository,
    comparison_repository,
)


class ComparisonService:
    def __init__(self, repository: ComparisonRepository = comparison_repository) -> None:
        self.repository = repository

    async def search_universities(
        self,
        db: AsyncSession,
        *,
        state: str | None = None,
        city: str | None = None,
        name: str | None = None,
        limit: int = 10,
    ) -> dict:
        _validate_search_filters(state=state, city=city, name=name)
        universities = await self.repository.search_universities(
            db,
            state=_clean_optional(state),
            city=_clean_optional(city),
            name=_clean_optional(name),
            limit=_limit(limit),
        )
        return {
            "results": universities,
            "metadata": {"count": len(universities), "source": "nnmc_catalog"},
        }

    async def compare_universities(self, db: AsyncSession, university_ids: list[str]) -> dict:
        ids = _validate_id_list(university_ids, "university_ids", minimum=2, maximum=5)
        universities = await self.repository.get_universities_by_ids(db, ids)
        return {
            "universities": universities,
            "metadata": {
                "requested_count": len(ids),
                "found_count": len(universities),
                "unavailable_fields": [
                    "rankings",
                    "tuition",
                    "placement_rates",
                    "acceptance_rates",
                    "scholarships",
                ],
            },
        }

    async def search_programs(
        self,
        db: AsyncSession,
        *,
        university_id: str | None = None,
        degree: str | None = None,
        name: str | None = None,
        limit: int = 20,
    ) -> dict:
        if university_id is not None:
            _validate_uuid(university_id, "university_id")
        if degree is None and name is None and university_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one program search filter is required",
            )
        programs = await self.repository.search_programs(
            db,
            university_id=_clean_optional(university_id),
            degree=_clean_optional(degree),
            name=_clean_optional(name),
            limit=_limit(limit),
        )
        return {"results": programs, "metadata": {"count": len(programs), "source": "nnmc_catalog"}}

    async def compare_programs(self, db: AsyncSession, program_ids: list[str]) -> dict:
        ids = _validate_id_list(program_ids, "program_ids", minimum=2, maximum=6)
        programs = await self.repository.get_programs_by_ids(db, ids)
        careers_by_program = await self.repository.get_careers_for_programs(db, ids)
        for program in programs:
            program["available_careers"] = careers_by_program.get(program["program_id"], [])
        return {
            "programs": programs,
            "metadata": {
                "requested_count": len(ids),
                "found_count": len(programs),
                "unavailable_fields": ["rankings", "salaries", "placement_rates", "tuition"],
            },
        }

    async def compare_career_paths(self, db: AsyncSession, program_ids: list[str]) -> dict:
        ids = _validate_id_list(program_ids, "program_ids", minimum=2, maximum=6)
        careers_by_program = await self.repository.get_careers_for_programs(db, ids)
        career_sets = {
            program_id: {career["career_id"] for career in careers}
            for program_id, careers in careers_by_program.items()
        }
        overlap_ids = set.intersection(*career_sets.values()) if career_sets else set()
        all_careers = {
            career["career_id"]: career
            for careers in careers_by_program.values()
            for career in careers
        }
        unique_by_program = {
            program_id: [career for career in careers if career["career_id"] not in overlap_ids]
            for program_id, careers in careers_by_program.items()
        }
        return {
            "mapped_careers": careers_by_program,
            "overlapping_careers": [
                all_careers[career_id]
                for career_id in sorted(
                    overlap_ids, key=lambda value: all_careers[value]["career_name"]
                )
            ],
            "unique_careers": unique_by_program,
            "metadata": {
                "source_tables": ["careers", "program_careers", "course_careers"],
                "message": (
                    None
                    if any(careers_by_program.values())
                    else "Career mapping information is not available in the current NNMC catalog."
                ),
            },
        }


def _clean_optional(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    return cleaned


def _validate_search_filters(**filters: str | None) -> None:
    if not any(_clean_optional(value) for value in filters.values()):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one university search filter is required",
        )


def _validate_id_list(
    values: list[str], field_name: str, *, minimum: int, maximum: int
) -> list[str]:
    if len(values) < minimum:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At least {minimum} {field_name} are required",
        )
    selected = values[:maximum]
    for value in selected:
        _validate_uuid(value, field_name.rstrip("s"))
    return selected


def _validate_uuid(value: str, field_name: str) -> None:
    try:
        uuid.UUID(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid {field_name}"
        ) from exc


def _limit(value: int) -> int:
    if value < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="limit must be greater than or equal to 1",
        )
    return min(value, 50)


comparison_service = ComparisonService()
