from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.student.domains.planning.services.graduation_audit_service import (
        GraduationAuditService,
    )


def _default_service():
    from app.student.domains.planning.services.graduation_audit_service import (
        graduation_audit_service,
    )

    return graduation_audit_service


class AuditPlanTool:
    name = "audit_plan"
    description = (
        "Audit a student education plan against catalog graduation requirements. "
        "Input: plan_id. Output: required credits, planned credits, missing courses, "
        "completion percentages, and graduation_ready status. Use for graduation "
        "readiness, remaining requirement, and acceleration questions."
    )
    parameters = {
        "type": "object",
        "properties": {"plan_id": {"type": "string"}},
        "required": ["plan_id"],
        "additionalProperties": False,
    }

    def __init__(self, service: GraduationAuditService | None = None) -> None:
        self.service = service

    async def execute(self, db: AsyncSession, plan_id: str) -> dict:
        service = self.service or _default_service()
        return await service.get_audit(db, plan_id)
