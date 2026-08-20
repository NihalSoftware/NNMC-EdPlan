from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.education_plan import CourseReschedule


async def create_reschedule(
    db: AsyncSession,
    *,
    user_id: int,
    payload: dict,
) -> CourseReschedule:
    entry = CourseReschedule(user_id=user_id, payload=payload)
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


async def get_reschedules(db: AsyncSession, *, user_id: int) -> Sequence[CourseReschedule]:
    result = await db.execute(select(CourseReschedule).where(CourseReschedule.user_id == user_id))
    return result.scalars().all()
