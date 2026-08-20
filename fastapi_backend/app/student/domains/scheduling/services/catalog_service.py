from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.student.domains.scheduling.repositories.catalog_repository import (
    CourseOfferingRepository,
    SectionMeetingRepository,
    SectionRepository,
    TermRepository,
    offering_repository,
    section_meeting_repository,
    section_repository,
    term_repository,
)


def _validate_uuid(value: str, field_name: str) -> None:
    try:
        uuid.UUID(str(value))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}",
        ) from exc


class TermService:
    def __init__(self, repository: TermRepository = term_repository) -> None:
        self.repository = repository

    async def list_terms(self, db: AsyncSession) -> list[dict]:
        return await self.repository.list_terms(db)

    async def get_term_by_id(self, db: AsyncSession, term_id: str) -> dict:
        _validate_uuid(term_id, "term_id")
        term = await self.repository.get_term_by_id(db, term_id)
        if not term:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Academic term not found",
            )
        return term


class CourseOfferingService:
    def __init__(self, repository: CourseOfferingRepository = offering_repository) -> None:
        self.repository = repository

    async def list_offerings_by_course(self, db: AsyncSession, course_id: str) -> list[dict]:
        _validate_uuid(course_id, "course_id")
        offerings = await self.repository.list_offerings_by_course(db, course_id)
        if offerings is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )
        return offerings

    async def get_offering_by_id(self, db: AsyncSession, offering_id: str) -> dict:
        _validate_uuid(offering_id, "offering_id")
        offering = await self.repository.get_offering_by_id(db, offering_id)
        if not offering:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course offering not found",
            )
        return offering


class SectionService:
    def __init__(self, repository: SectionRepository = section_repository) -> None:
        self.repository = repository

    async def list_sections_by_offering(self, db: AsyncSession, offering_id: str) -> list[dict]:
        _validate_uuid(offering_id, "offering_id")
        sections = await self.repository.list_sections_by_offering(db, offering_id)
        if sections is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course offering not found",
            )
        return sections

    async def get_section_by_id(self, db: AsyncSession, section_id: str) -> dict:
        _validate_uuid(section_id, "section_id")
        section = await self.repository.get_section_by_id(db, section_id)
        if not section:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found",
            )
        return section


class SectionMeetingService:
    def __init__(self, repository: SectionMeetingRepository = section_meeting_repository) -> None:
        self.repository = repository

    async def list_meetings_by_section(self, db: AsyncSession, section_id: str) -> list[dict]:
        _validate_uuid(section_id, "section_id")
        meetings = await self.repository.list_meetings_by_section(db, section_id)
        if meetings is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Section not found",
            )
        return meetings


term_service = TermService()
offering_service = CourseOfferingService()
section_service = SectionService()
section_meeting_service = SectionMeetingService()
