from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.security.auth import get_current_user
from app.student.domains.planning.schemas.education import RescheduleRequest
from app.student.domains.planning.services import education_plan_service

router = APIRouter(tags=["users"])


@router.post("/users/education-plan/reschedule")
async def reschedule_courses(
    request: RescheduleRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    payload = await education_plan_service.save_reschedule_for_request(db, current_user, request)
    return {"success": True, "message": "Reschedule request queued", "data": payload}
