from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.student.domains.planning.schemas.normalized_plan import (
    PlanCreateRequest,
    PlanUpdateRequest,
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


class CreatePlanTool:
    name = "create_plan"
    description = (
        "Create a new student education plan. Input: payload with user_id, "
        "university_id, program_id, plan_name, optional description, and is_active. "
        "Output: created plan details. Use for explicit new-plan requests only."
    )
    parameters = {
        "type": "object",
        "properties": {
            "payload": {
                "type": "object",
                "properties": {
                    "user_id": {"type": "integer"},
                    "university_id": {"type": "string"},
                    "program_id": {"type": "string"},
                    "plan_name": {"type": "string"},
                    "description": {"type": ["string", "null"]},
                    "is_active": {"type": "boolean"},
                },
                "required": ["user_id", "university_id", "program_id", "plan_name"],
                "additionalProperties": False,
            }
        },
        "required": ["payload"],
        "additionalProperties": False,
    }

    def __init__(self, service: NormalizedPlanService | None = None) -> None:
        self.service = service

    async def execute(
        self,
        db: AsyncSession,
        payload: PlanCreateRequest | dict[str, Any],
    ) -> dict:
        service = self.service or _default_service()
        return await service.create_plan(db, coerce_payload(PlanCreateRequest, payload))


class UpdatePlanTool:
    name = "update_plan"
    description = (
        "Update plan metadata. Input: plan_id and payload with plan_name, description, "
        "or is_active. Output: updated plan details. Use for explicit rename, "
        "description, or activation changes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "plan_id": {"type": "string"},
            "payload": {
                "type": "object",
                "properties": {
                    "plan_name": {"type": "string"},
                    "description": {"type": ["string", "null"]},
                    "is_active": {"type": "boolean"},
                },
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
        payload: PlanUpdateRequest | dict[str, Any],
    ) -> dict:
        service = self.service or _default_service()
        return await service.update_plan(
            db,
            plan_id,
            coerce_payload(PlanUpdateRequest, payload),
        )


class DeletePlanTool:
    name = "delete_plan"
    description = (
        "Deactivate/delete a student education plan. Input: plan_id. Output: updated "
        "inactive plan details. Use only when the student explicitly asks to delete "
        "or deactivate a plan."
    )
    parameters = {
        "type": "object",
        "properties": {"plan_id": {"type": "string"}},
        "required": ["plan_id"],
        "additionalProperties": False,
    }

    def __init__(self, service: NormalizedPlanService | None = None) -> None:
        self.service = service

    async def execute(self, db: AsyncSession, plan_id: str) -> dict:
        service = self.service or _default_service()
        return await service.deactivate_plan(db, plan_id)


class GetPlanTool:
    name = "get_plan"
    description = (
        "Read a student education plan and planned courses. Input: plan_id. Output: "
        "plan details, term credit totals, and planned courses. Use before advising, "
        "validating assumptions, or comparing candidate paths."
    )
    parameters = {
        "type": "object",
        "properties": {"plan_id": {"type": "string"}},
        "required": ["plan_id"],
        "additionalProperties": False,
    }

    def __init__(self, service: NormalizedPlanService | None = None) -> None:
        self.service = service

    async def execute(self, db: AsyncSession, plan_id: str) -> dict:
        service = self.service or _default_service()
        return await service.get_plan_by_id(db, plan_id)
