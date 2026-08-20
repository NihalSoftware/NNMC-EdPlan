from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.student.domains.comparison.schemas.comparison import (
    CareerPathCompareRequest,
    ProgramCompareRequest,
    ProgramSearchRequest,
)
from app.student.domains.comparison.tools._payloads import coerce_payload

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.student.domains.comparison.services.comparison_service import ComparisonService


def _default_service():
    from app.student.domains.comparison.services.comparison_service import comparison_service

    return comparison_service


class SearchProgramsTool:
    name = "search_programs"
    description = (
        "Search academic programs in the NNMC catalog by university_id, degree, or "
        "program name. Output includes matching program facts."
    )
    parameters = {
        "type": "object",
        "properties": {
            "payload": {
                "type": "object",
                "properties": {
                    "university_id": {"type": ["string", "null"]},
                    "degree": {"type": ["string", "null"]},
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
        payload: ProgramSearchRequest | dict[str, Any],
    ) -> dict:
        request = coerce_payload(ProgramSearchRequest, payload)
        service = self.service or _default_service()
        return await service.search_programs(
            db,
            university_id=request.university_id,
            degree=request.degree,
            name=request.name,
            limit=request.limit,
        )


class CompareProgramsTool:
    name = "compare_programs"
    description = (
        "Compare NNMC academic programs using only catalog facts. Input: program_ids. "
        "Output compares credits, duration when available, required courses, mapped careers "
        "when available, and program description when available."
    )
    parameters = {
        "type": "object",
        "properties": {
            "program_ids": {
                "type": "array",
                "items": {"type": "string"},
                "minItems": 2,
                "maxItems": 6,
            }
        },
        "required": ["program_ids"],
        "additionalProperties": False,
    }

    def __init__(self, service: ComparisonService | None = None) -> None:
        self.service = service

    async def execute(
        self,
        db: AsyncSession,
        program_ids: list[str] | ProgramCompareRequest | dict[str, Any],
    ) -> dict:
        request = _coerce_program_ids(ProgramCompareRequest, program_ids)
        service = self.service or _default_service()
        return await service.compare_programs(db, request.program_ids)


class CompareCareerPathsTool:
    name = "compare_career_paths"
    description = (
        "Compare career mappings associated with NNMC programs using catalog careers, "
        "program_careers, and course_careers tables when available. Output includes "
        "mapped, overlapping, and unique careers."
    )
    parameters = CompareProgramsTool.parameters

    def __init__(self, service: ComparisonService | None = None) -> None:
        self.service = service

    async def execute(
        self,
        db: AsyncSession,
        program_ids: list[str] | CareerPathCompareRequest | dict[str, Any],
    ) -> dict:
        request = _coerce_program_ids(CareerPathCompareRequest, program_ids)
        service = self.service or _default_service()
        return await service.compare_career_paths(db, request.program_ids)


def _coerce_program_ids(schema, value):
    if isinstance(value, list):
        return schema(program_ids=value)
    return coerce_payload(schema, value)
