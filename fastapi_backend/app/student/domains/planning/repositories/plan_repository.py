from collections.abc import Sequence

from sqlalchemy import and_, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.education_plan import EducationPlan, ProgramCourse
from app.shared.constants.institution import NORTHERN_NEW_MEXICO_COLLEGE_NAME
from app.student.domains.planning.schemas.education import ProgramCoursePayload


async def get_plan(
    db: AsyncSession,
    *,
    user_id: int | None = None,
    program_name: str,
    university_name: str,
) -> Sequence[EducationPlan]:
    conditions = [
        EducationPlan.program_name == program_name,
        EducationPlan.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME),
    ]
    if user_id is not None:
        conditions.append(EducationPlan.user_id == user_id)
    result = await db.execute(select(EducationPlan).where(and_(*conditions)))
    return result.scalars().all()


async def list_plans(db: AsyncSession, *, user_id: int) -> Sequence[EducationPlan]:
    result = await db.execute(
        select(EducationPlan).where(
            EducationPlan.user_id == user_id,
            EducationPlan.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME),
        )
    )
    return result.scalars().all()


async def create_plan(
    db: AsyncSession,
    *,
    user_id: int,
    program_name: str,
    university_name: str,
    degree: str | None,
    payload: dict,
) -> EducationPlan:
    plan = EducationPlan(
        user_id=user_id,
        program_name=program_name,
        university_name=university_name,
        degree=degree,
        payload=payload,
    )
    db.add(plan)
    await db.flush()
    return plan


async def update_plan(
    plan: EducationPlan,
    *,
    payload: dict,
    degree: str | None,
) -> EducationPlan:
    plan.payload = payload
    if degree:
        plan.degree = degree
    return plan


async def delete_plan(db: AsyncSession, plan: EducationPlan) -> None:
    await db.delete(plan)
    await db.commit()


async def persist_courses(
    db: AsyncSession,
    *,
    plan: EducationPlan,
    courses: Sequence[ProgramCoursePayload],
) -> None:
    for entry in courses:
        db.add(
            ProgramCourse(
                education_plan_id=plan.id,
                year_label=entry.year,
                semester_label=entry.semester,
                course_code=entry.code,
                course_name=entry.course_name,
                credits=entry.credits,
                prerequisite=entry.prerequisite,
                corequisite=entry.corequisite,
                schedule=(
                    entry.schedule.model_dump()
                    if entry.schedule is not None and hasattr(entry.schedule, "model_dump")
                    else entry.schedule
                ),
            )
        )


async def delete_program_courses(db: AsyncSession, *, education_plan_id: int) -> None:
    await db.execute(
        delete(ProgramCourse).where(ProgramCourse.education_plan_id == education_plan_id)
    )
