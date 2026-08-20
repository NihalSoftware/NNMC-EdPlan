from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.security.auth import get_current_user
from app.student.domains.planning.schemas.education import (
    EducationPlanDeleteRequest,
    EducationPlanListQuery,
    EducationPlanQuery,
    EducationPlanRequest,
)
from app.student.domains.planning.services import education_plan_service

router = APIRouter(tags=["users"])


@router.post("/users/education-plan")
async def add_education_plan(
    request: EducationPlanRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    payload = await education_plan_service.add_or_replace_plan_for_request(
        db, current_user, request
    )
    return {"success": True, "message": "Education plan saved", "data": payload}


@router.post("/users/education-plan/query")
async def query_education_plan(
    request: EducationPlanQuery,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    payload = await education_plan_service.query_plan_payload(db, current_user, request)
    if payload is None:
        return {"success": True, "message": "No education plan found", "data": None}
    return {"success": True, "message": "Plan retrieved", "data": payload}


@router.post("/users/education-plan/list")
async def list_plans(
    request: EducationPlanListQuery,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    data = await education_plan_service.list_plan_payloads(db, current_user, request)
    return {"success": True, "message": "Plans loaded", "data": data}


@router.post("/users/education-plan/delete")
async def delete_plan(
    request: EducationPlanDeleteRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    await education_plan_service.delete_plan_for_request(db, current_user, request)
    return {"success": True, "message": "Education plan deleted", "data": None}
