from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.student.domains.planning.schemas.normalized_plan import (
    PlanCourseCreateRequest,
    PlanCourseUpdateRequest,
)
from app.student.domains.planning.tools._payloads import coerce_payload

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.student.domains.planning.services.normalized_plan_service import (
        NormalizedPlanService,
    )


def _default_service():
    from app.student.domains.planning.services.normalized_plan_service import (
        normalized_plan_service,
    )

    return normalized_plan_service


class AddCourseTool:
    name = "add_course"
    description = (
        "Add a course to a student education plan. Input: plan_id and payload with "
        "course_id, optional planned_term_id, status, and notes. Output: created "
        "planned-course record. Use for explicit add-course requests after course "
        "identity is known."
    )
    parameters = {
        "type": "object",
        "properties": {
            "plan_id": {"type": "string"},
            "payload": {
                "type": "object",
                "properties": {
                    "course_id": {"type": "string"},
                    "planned_term_id": {"type": ["string", "null"]},
                    "status": {"type": "string", "enum": ["Planned", "In Progress", "Completed"]},
                    "notes": {"type": ["string", "null"]},
                },
                "required": ["course_id"],
                "additionalProperties": False,
            },
        },
        "required": ["plan_id", "payload"],
        "additionalProperties": False,
    }

    def __init__(self, service: NormalizedPlanService | None = None) -> None:
        self.service = service

    async def execute(
        self,
        db: AsyncSession,
        plan_id: str,
        payload: PlanCourseCreateRequest | dict[str, Any],
    ) -> dict:
        service = self.service or _default_service()
        return await service.add_plan_course(
            db,
            plan_id,
            coerce_payload(PlanCourseCreateRequest, payload),
        )


class RemoveCourseTool:
    name = "remove_course"
    description = (
        "Remove a course from a student education plan. Input: plan_id and course_id. "
        "Output: no content on success. Use only for explicit remove/drop-course "
        "requests."
    )
    parameters = {
        "type": "object",
        "properties": {
            "plan_id": {"type": "string"},
            "course_id": {"type": "string"},
        },
        "required": ["plan_id", "course_id"],
        "additionalProperties": False,
    }

    def __init__(self, service: NormalizedPlanService | None = None) -> None:
        self.service = service

    async def execute(self, db: AsyncSession, plan_id: str, course_id: str) -> None:
        service = self.service or _default_service()
        await service.delete_plan_course(db, plan_id, course_id)


class MoveCourseTool:
    name = "move_course"
    description = (
        "Move or update a planned course. Input: plan_id, course_id, and payload with "
        "planned_term_id, status, or notes. Output: updated planned-course record. "
        "Use when the student asks to move a course to another term or adjust its "
        "planning status."
    )
    parameters = {
        "type": "object",
        "properties": {
            "plan_id": {"type": "string"},
            "course_id": {"type": "string"},
            "payload": {
                "type": "object",
                "properties": {
                    "planned_term_id": {"type": ["string", "null"]},
                    "status": {"type": "string", "enum": ["Planned", "In Progress", "Completed"]},
                    "notes": {"type": ["string", "null"]},
                },
                "additionalProperties": False,
            },
        },
        "required": ["plan_id", "course_id", "payload"],
        "additionalProperties": False,
    }

    def __init__(self, service: NormalizedPlanService | None = None) -> None:
        self.service = service

    async def execute(
        self,
        db: AsyncSession,
        plan_id: str,
        course_id: str,
        payload: PlanCourseUpdateRequest | dict[str, Any],
    ) -> dict:
        service = self.service or _default_service()
        return await service.update_plan_course(
            db,
            plan_id,
            course_id,
            coerce_payload(PlanCourseUpdateRequest, payload),
        )
