from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.agentic import ConversationMemory, StudentPreference
from app.models.education_plan import CourseSchedule, EducationPlan
from app.models.user import User
from app.orchestrator.schemas.student_context import StudentContext
from app.shared.constants.institution import NORTHERN_NEW_MEXICO_COLLEGE_NAME
from app.student.domains.discovery.models import University
from app.student.domains.planning.models import EdPlan

logger = logging.getLogger(__name__)


class ContextLoaderError(Exception):
    """Base exception raised by the orchestrator context loader."""


class UserNotFoundError(ContextLoaderError):
    """Raised when the requested student user cannot be found."""


class PlanNotFoundError(ContextLoaderError):
    """Raised when the requested education plan cannot be found."""


class ProgramNotFoundError(ContextLoaderError):
    """Raised when program context cannot be resolved from existing plan data."""


class UniversityNotFoundError(ContextLoaderError):
    """Raised when university context cannot be resolved from existing plan data."""


class ContextLoader:
    """Loads student context data needed by the orchestrator workflow."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def load(self, user_id: int, plan_id: UUID, query: str) -> StudentContext:
        """Load and assemble the student context for an orchestrator run."""
        if user_id <= 0:
            raise ValueError("user_id must be greater than zero.")
        if not query.strip():
            raise ValueError("query is required.")

        user = await self._load_user(user_id)
        if user is None:
            raise UserNotFoundError(f"User not found: {user_id}")

        plan = await self._load_plan(user_id, plan_id)
        if plan is None:
            raise PlanNotFoundError(f"Plan not found: {plan_id}")

        operational_plan = await self._load_operational_plan(user_id)
        if operational_plan is None or not operational_plan.program_name:
            raise ProgramNotFoundError(f"Program not found for user_id={user_id}")
        if not operational_plan.university_name:
            raise UniversityNotFoundError(f"University not found for user_id={user_id}")

        schedules = await self._load_course_schedules(operational_plan)
        preferences = await self._load_preferences(user_id)
        memory = await self._load_memory(user_id, plan_id)

        logger.debug("Loaded student context user_id=%s plan_id=%s", user_id, plan_id)
        return StudentContext(
            user=self._serialize_user(user),
            plan=self._serialize_plan(plan, operational_plan),
            program=self._serialize_program(operational_plan),
            university=self._serialize_university(operational_plan),
            completed_courses=self._serialize_courses(operational_plan, schedules),
            preferences=[self._serialize_preference(item) for item in preferences],
            memory=[self._serialize_memory(item) for item in memory],
            career_goal=self._extract_career_goal(preferences),
        )

    async def _load_user(self, user_id: int) -> User | None:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def _load_plan(self, user_id: int, plan_id: UUID) -> EdPlan | None:
        result = await self.db.execute(
            select(EdPlan).where(
                EdPlan.plan_id == plan_id,
                EdPlan.user_id == user_id,
                EdPlan.university.has(
                    University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
                ),
            )
        )
        return result.scalar_one_or_none()

    async def _load_operational_plan(self, user_id: int) -> EducationPlan | None:
        result = await self.db.execute(
            select(EducationPlan)
            .where(
                EducationPlan.user_id == user_id,
                EducationPlan.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME),
            )
            .options(selectinload(EducationPlan.courses))
            .order_by(EducationPlan.updated_at.desc(), EducationPlan.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _load_course_schedules(
        self, operational_plan: EducationPlan | None
    ) -> list[CourseSchedule]:
        if operational_plan is None:
            return []
        result = await self.db.execute(
            select(CourseSchedule).where(CourseSchedule.education_plan_id == operational_plan.id)
        )
        return list(result.scalars().all())

    async def _load_preferences(self, user_id: int) -> list[StudentPreference]:
        result = await self.db.execute(
            select(StudentPreference)
            .where(StudentPreference.user_id == user_id)
            .order_by(StudentPreference.updated_at.desc())
        )
        return list(result.scalars().all())

    async def _load_memory(self, user_id: int, plan_id: UUID) -> list[ConversationMemory]:
        result = await self.db.execute(
            select(ConversationMemory)
            .where(ConversationMemory.user_id == user_id, ConversationMemory.plan_id == plan_id)
            .order_by(ConversationMemory.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    def _serialize_user(user: User) -> dict[str, Any]:
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone_number": user.phone_number,
            "role": getattr(user.role, "value", user.role),
            "is_active": user.is_active,
            "is_deactivated": user.is_deactivated,
        }

    @staticmethod
    def _serialize_plan(
        plan_model: EdPlan, operational_plan: EducationPlan | None
    ) -> dict[str, Any]:
        plan: dict[str, Any] = {"plan_id": str(plan_model.plan_id)}
        if operational_plan is not None:
            plan.update(
                {
                    "education_plan_id": operational_plan.id,
                    "program_name": operational_plan.program_name,
                    "university_name": operational_plan.university_name,
                    "degree": operational_plan.degree,
                    "payload": operational_plan.payload,
                    "created_at": operational_plan.created_at,
                    "updated_at": operational_plan.updated_at,
                }
            )
        return plan

    @staticmethod
    def _serialize_program(operational_plan: EducationPlan | None) -> dict[str, Any] | None:
        if operational_plan is None:
            return None
        return {
            "name": operational_plan.program_name,
            "degree": operational_plan.degree,
        }

    @staticmethod
    def _serialize_university(operational_plan: EducationPlan | None) -> dict[str, Any] | None:
        if operational_plan is None:
            return None
        return {"name": operational_plan.university_name}

    @staticmethod
    def _serialize_courses(
        operational_plan: EducationPlan | None, schedules: list[CourseSchedule]
    ) -> list[dict[str, Any]]:
        if operational_plan is None:
            return []

        schedules_by_course_id: dict[int, list[CourseSchedule]] = {}
        for schedule in schedules:
            schedules_by_course_id.setdefault(schedule.course_id, []).append(schedule)

        courses: list[dict[str, Any]] = []
        for course in operational_plan.courses:
            courses.append(
                {
                    "id": course.id,
                    "year": course.year_label,
                    "semester": course.semester_label,
                    "code": course.course_code,
                    "course_name": course.course_name,
                    "credits": course.credits,
                    "prerequisite": course.prerequisite,
                    "corequisite": course.corequisite,
                    "schedule": course.schedule,
                    "available_schedules": [
                        {
                            "id": item.id,
                            "day": item.day,
                            "time": item.time,
                            "available": item.available,
                        }
                        for item in schedules_by_course_id.get(course.id, [])
                    ],
                }
            )
        return courses

    @staticmethod
    def _serialize_preference(preference: StudentPreference) -> dict[str, Any]:
        return {
            "preference_id": str(preference.preference_id),
            "key": preference.preference_key,
            "value": preference.preference_value,
            "updated_at": preference.updated_at,
        }

    @staticmethod
    def _serialize_memory(memory: ConversationMemory) -> dict[str, Any]:
        return {
            "memory_id": str(memory.memory_id),
            "run_id": str(memory.run_id),
            "summary": memory.summary,
            "created_at": memory.created_at,
        }

    @staticmethod
    def _extract_career_goal(preferences: list[StudentPreference]) -> str | None:
        for preference in preferences:
            if preference.preference_key.strip().lower() == "career_goal":
                return preference.preference_value
        return None
