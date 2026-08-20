from __future__ import annotations

import logging
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.security.auth import get_current_user
from app.student.domains.onboarding.services import intake_service

router = APIRouter(prefix="/intake", tags=["intake"])
logger = logging.getLogger(__name__)


class IntakeSubmissionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    high_school_name: str = Field(min_length=1, max_length=200)
    graduation_year: int = Field(ge=2000, le=2100)
    state: str = Field(min_length=2, max_length=40)
    resident_status: Literal["In state", "Out of state", "International"]
    gpa: float = Field(ge=0, le=4)
    class_rank: str | None = Field(default=None, max_length=40)
    student_type: str = Field(min_length=1, max_length=60)
    grade_english: str = Field(min_length=1, max_length=12)
    grade_math: str = Field(min_length=1, max_length=12)
    grade_science: str = Field(min_length=1, max_length=12)
    grade_social_studies: str = Field(min_length=1, max_length=12)
    sat_taken: Literal["yes", "no"] = "no"
    sat_total: int | None = Field(default=None, ge=0, le=1600)
    sat_math: int | None = Field(default=None, ge=0, le=800)
    sat_reading: int | None = Field(default=None, ge=0, le=800)
    sat_date: date | None = None
    act_taken: Literal["yes", "no"] = "no"
    act_composite: int | None = Field(default=None, ge=1, le=36)
    act_english: int | None = Field(default=None, ge=1, le=36)
    act_math: int | None = Field(default=None, ge=1, le=36)
    act_reading: int | None = Field(default=None, ge=1, le=36)
    act_science: int | None = Field(default=None, ge=1, le=36)
    act_date: date | None = None
    budget_total: int = Field(ge=0, le=10_000_000)
    max_tuition: int = Field(ge=0, le=10_000_000)
    need_aid: str | None = Field(default=None, max_length=40)
    pay_options: str | list[str] | None = None
    work_study: Literal["yes", "no"] | None = None
    consent: Literal[True]

    @field_validator("pay_options")
    @classmethod
    def validate_pay_options(cls, value: str | list[str] | None):
        if value is None:
            return value
        values = [value] if isinstance(value, str) else value
        if len(values) > 10 or any(len(option) > 80 for option in values):
            raise ValueError("Pay options must contain at most 10 short values")
        return value


@router.post("")
async def save_intake(
    payload: IntakeSubmissionRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: AsyncSession = Depends(get_db),
):
    """Save intake form submission to the database."""
    try:
        submission = payload.model_dump(mode="json")
        submission["user_id"] = current_user.id
        entry = await intake_service.save_submission(db, submission)
        return {"success": True, "message": "Saved", "data": {"id": entry.id}}
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception("Failed to save intake submission")
        raise HTTPException(status_code=500, detail="Failed to save intake data") from exc
