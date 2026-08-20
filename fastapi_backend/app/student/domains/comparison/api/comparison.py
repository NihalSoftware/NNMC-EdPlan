from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.student.domains.comparison.schemas.comparison import (
    CareerPathCompareRequest,
    ProgramCompareRequest,
    ProgramSearchRequest,
    UniversityCompareRequest,
    UniversitySearchRequest,
)
from app.student.domains.comparison.services.comparison_service import comparison_service

router = APIRouter(prefix="/comparison", tags=["comparison"])


@router.post("/universities/search")
async def search_universities(request: UniversitySearchRequest, db: AsyncSession = Depends(get_db)):
    return _success(await comparison_service.search_universities(db, **request.model_dump()))


@router.post("/universities/compare")
async def compare_universities(
    request: UniversityCompareRequest, db: AsyncSession = Depends(get_db)
):
    return _success(await comparison_service.compare_universities(db, request.university_ids))


@router.post("/programs/search")
async def search_programs(request: ProgramSearchRequest, db: AsyncSession = Depends(get_db)):
    return _success(await comparison_service.search_programs(db, **request.model_dump()))


@router.post("/programs/compare")
async def compare_programs(request: ProgramCompareRequest, db: AsyncSession = Depends(get_db)):
    return _success(await comparison_service.compare_programs(db, request.program_ids))


@router.post("/careers/compare")
async def compare_career_paths(
    request: CareerPathCompareRequest, db: AsyncSession = Depends(get_db)
):
    return _success(await comparison_service.compare_career_paths(db, request.program_ids))


def _success(data: dict) -> dict:
    return {"success": True, "data": data}
