from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.student.domains.comparison.schemas.comparison import (
    UniversityCompareRequest,
    UniversitySearchRequest,
)
from app.student.domains.comparison.tools._payloads import coerce_payload

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.student.domains.comparison.services.comparison_service import ComparisonService


def _default_service():
    from app.student.domains.comparison.services.comparison_service import comparison_service

    return comparison_service


class SearchUniversitiesTool:
    name = "search_universities"
    description = (
        "Return Northern New Mexico College from the NNMC catalog. "
        "Output includes university id, name, location, website, and available programs."
    )
    parameters = {
        "type": "object",
        "properties": {
            "payload": {
                "type": "object",
                "properties": {
                    "state": {"type": ["string", "null"]},
                    "city": {"type": ["string", "null"]},
                    "name": {"type": ["string", "null"]},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "additionalProperties": False,
            }
        },
        "required": ["payload"],
        "additionalProperties": False,
    }

    def __init__(self, service: ComparisonService | None = None) -> None:
        self.service = service

    async def execute(
        self,
        db: AsyncSession,
        payload: UniversitySearchRequest | dict[str, Any],
    ) -> dict:
        request = coerce_payload(UniversitySearchRequest, payload)
        service = self.service or _default_service()
        return await service.search_universities(
            db,
            state=request.state,
            city=request.city,
            name=request.name,
            limit=request.limit,
        )


class CompareUniversitiesTool:
    name = "compare_universities"
    description = (
        "Institution comparison is retained for API compatibility but the NNMC catalog "
        "contains only Northern New Mexico College. Input: "
        "university_ids. Output compares location, available programs, program count, "
        "public/private when available, website, and catalog information."
    )
    parameters = {
        "type": "object",
        "properties": {
            "university_ids": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 5,
            }
        },
        "required": ["university_ids"],
        "additionalProperties": False,
    }

    def __init__(self, service: ComparisonService | None = None) -> None:
        self.service = service

    async def execute(
        self,
        db: AsyncSession,
        university_ids: list[str] | UniversityCompareRequest | dict[str, Any],
    ) -> dict:
        if isinstance(university_ids, list):
            request = UniversityCompareRequest(university_ids=university_ids)
        else:
            request = coerce_payload(UniversityCompareRequest, university_ids)
        service = self.service or _default_service()
        return await service.compare_universities(db, request.university_ids)
