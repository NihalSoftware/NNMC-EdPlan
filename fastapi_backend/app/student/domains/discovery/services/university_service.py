from __future__ import annotations

import asyncio
import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.constants.institution import (
    NORTHERN_NEW_MEXICO_COLLEGE_NAME,
    NORTHERN_NEW_MEXICO_COLLEGE_SCORECARD_ID,
)
from app.student.domains.discovery.clients.college_scorecard import (
    CollegeScorecardClient,
)
from app.student.domains.discovery.clients.college_scorecard import (
    client as college_scorecard_client,
)
from app.student.domains.discovery.repositories.university_repository import (
    UniversityRepository,
    university_repository,
)


def _clean_filter(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} cannot be blank",
        )
    return cleaned


def _validate_uuid(value: str, field_name: str) -> None:
    try:
        uuid.UUID(str(value))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}",
        ) from exc


class UniversityService:
    def __init__(
        self,
        repository: UniversityRepository = university_repository,
        scorecard_client: CollegeScorecardClient = college_scorecard_client,
    ) -> None:
        self.repository = repository
        self.scorecard_client = scorecard_client

    async def search_universities(
        self,
        db: AsyncSession,
        *,
        search: str | None = None,
        state: str | None = None,
        page: int = 0,
        per_page: int = 10,
    ) -> dict:
        if page < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="page must be greater than or equal to 0",
            )
        if per_page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="per_page must be greater than or equal to 1",
            )

        search = _clean_filter(search, "search")
        state = _clean_filter(state, "state")
        universities = await self.repository.list_universities(
            db,
            search=search,
            state=state,
            offset=page * per_page,
            limit=per_page,
        )
        enriched_universities = await self._enrich_many_with_scorecard(universities)
        return {
            "results": enriched_universities,
            "metadata": {
                "count": len(enriched_universities),
                "page": page,
                "per_page": per_page,
                "source": "Northern New Mexico College catalog and College Scorecard",
            },
        }

    async def get_university(self, db: AsyncSession, university_id: str) -> dict:
        _validate_uuid(university_id, "university_id")
        university = await self.repository.get_university_by_id(db, university_id)
        if not university:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="University not found",
            )
        return await self._enrich_with_scorecard(university)

    async def compare_universities(self, db: AsyncSession, university_ids: list[str]) -> list[dict]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"College comparison is not available in the dedicated "
                f"{NORTHERN_NEW_MEXICO_COLLEGE_NAME} site"
            ),
        )

    async def _enrich_with_scorecard(self, university: dict) -> dict:
        try:
            scorecard = await self.scorecard_client.get_school(
                NORTHERN_NEW_MEXICO_COLLEGE_SCORECARD_ID
            )
        except Exception:
            return university
        if not scorecard:
            return university
        return _merge_university_data(university, scorecard)

    async def _enrich_many_with_scorecard(
        self,
        universities: list[dict],
    ) -> list[dict]:
        if not universities:
            return []
        try:
            scorecard = await self.scorecard_client.get_school(
                NORTHERN_NEW_MEXICO_COLLEGE_SCORECARD_ID
            )
            scorecards = [scorecard for _ in universities]
        except Exception:
            return list(
                await asyncio.gather(*(self._enrich_with_scorecard(item) for item in universities))
            )

        return [
            _merge_university_data(university, scorecard) if scorecard else university
            for university, scorecard in zip(universities, scorecards, strict=True)
        ]


university_service = UniversityService()


def _merge_university_data(university: dict, scorecard: dict) -> dict:
    merged = dict(university)
    preserve_keys = {"unit_id", "university_id", "university_name", "name", "city", "state"}

    for key, value in scorecard.items():
        if key in preserve_keys:
            continue
        if value is not None:
            merged[key] = value

    merged["scorecard_unit_id"] = scorecard.get("scorecard_unit_id") or scorecard.get("unit_id")
    merged["scorecard_source_url"] = scorecard.get("scorecard_source_url")
    merged["compare_data_source"] = "college_scorecard"
    merged["website"] = university.get("website") or scorecard.get("website")

    scorecard_info = scorecard.get("college_info") or {}
    university_info = university.get("college_info") or {}
    merged["college_info"] = {**scorecard_info, **university_info}
    if scorecard.get("organization_type"):
        merged["college_info"]["type"] = scorecard.get("organization_type")
    if scorecard.get("location_type"):
        merged["college_info"]["setting"] = scorecard.get("location_type")

    return merged


async def search_universities(
    db: AsyncSession,
    *,
    search: str | None = None,
    state: str | None = None,
    page: int = 0,
    per_page: int = 10,
) -> dict:
    return await university_service.search_universities(
        db,
        page=page,
        per_page=per_page,
        search=search,
        state=state,
    )


async def get_university(db: AsyncSession, university_id: str) -> dict:
    return await university_service.get_university(db, university_id)


async def compare_universities(db: AsyncSession, university_ids: list[str]) -> list[dict]:
    return await university_service.compare_universities(db, university_ids)
