from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.security.auth import get_current_user
from app.student.domains.planning.schemas.graduation_audit import (
    GraduationAuditResult,
)
from app.student.domains.planning.services.graduation_audit_service import (
    graduation_audit_service,
)

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get("/{plan_id}/audit", response_model=GraduationAuditResult)
async def get_graduation_audit(
    plan_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    return await graduation_audit_service.get_audit(db, plan_id, expected_user_id=current_user.id)
