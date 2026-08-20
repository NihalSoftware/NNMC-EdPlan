from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.student.domains.planning.schemas.planning_validation import PlanValidationRequest
from app.student.domains.planning.tools._payloads import coerce_payload

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.student.domains.planning.services.planning_validation_service import (
        PlanningValidationService,
    )


def _default_service():
    from app.student.domains.planning.services.planning_validation_service import (
        planning_validation_service,
    )

    return planning_validation_service


class ValidatePlanTool:
    name = "validate_plan"
    description = (
        "Validate a student education plan against duplicate, prerequisite, "
        "corequisite, and credit-load rules. Input: plan_id and optional payload "
        "with mode save or draft. Output: validation result and issues. Use before "
        "recommending a plan or after proposed course changes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "plan_id": {"type": "string"},
            "payload": {
                "type": "object",
                "properties": {"mode": {"type": "string", "enum": ["save", "draft"]}},
                "additionalProperties": False,
            },
        },
        "required": ["plan_id"],
        "additionalProperties": False,
    }

    def __init__(
        self,
        service: PlanningValidationService | None = None,
    ) -> None:
        self.service = service

    async def execute(
        self,
        db: AsyncSession,
        plan_id: str,
        payload: PlanValidationRequest | dict[str, Any] | None = None,
    ) -> dict:
        request = None if payload is None else coerce_payload(PlanValidationRequest, payload)
        service = self.service or _default_service()
        return await service.validate_plan(db, plan_id, request)
