from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.student.domains.onboarding.models.intake import IntakeSubmission


async def create_submission(db: AsyncSession, payload: dict[str, Any]) -> IntakeSubmission:
    entry = IntakeSubmission(payload=payload)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_submission(db: AsyncSession, submission_id: int) -> IntakeSubmission | None:
    return await db.get(IntakeSubmission, submission_id)


async def list_submissions(db: AsyncSession) -> Sequence[IntakeSubmission]:
    result = await db.execute(
        select(IntakeSubmission).order_by(IntakeSubmission.submitted_at.desc())
    )
    return result.scalars().all()
