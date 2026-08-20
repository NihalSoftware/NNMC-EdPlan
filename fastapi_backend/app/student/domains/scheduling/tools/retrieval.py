from __future__ import annotations

from typing import TYPE_CHECKING

from app.student.domains.scheduling.services.retrieval_service import (
    SchedulePilotRetrievalService,
    schedulepilot_retrieval_service,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class _RetrievalTool:
    name: str
    description: str
    parameters: dict

    def __init__(self, service: SchedulePilotRetrievalService | None = None) -> None:
        self.service = service or schedulepilot_retrieval_service


class GetStudentPlanTool(_RetrievalTool):
    name = "get_student_plan"
    description = "Read a verified student plan by user_id and plan_id."
    parameters = {
        "type": "object",
        "properties": {"user_id": {"type": "integer"}, "plan_id": {"type": "string"}},
        "required": ["user_id", "plan_id"],
        "additionalProperties": False,
    }

    async def execute(self, db: AsyncSession, *, user_id: int, plan_id: str):
        return await self.service.get_student_plan(db, user_id=user_id, plan_id=plan_id)


class GetPlanCoursesTool(_RetrievalTool):
    name = "get_plan_courses"
    description = "Read planned courses, credits, planned terms, and statuses for a plan."
    parameters = {
        "type": "object",
        "properties": {"plan_id": {"type": "string"}},
        "required": ["plan_id"],
        "additionalProperties": False,
    }

    async def execute(self, db: AsyncSession, *, plan_id: str):
        return await self.service.get_plan_courses(db, plan_id=plan_id)


class GetAvailableTermsTool(_RetrievalTool):
    name = "get_available_terms"
    description = "Read active academic terms available for scheduling."
    parameters = {"type": "object", "properties": {}, "additionalProperties": False}

    async def execute(self, db: AsyncSession):
        return await self.service.get_available_terms(db)


class GetCourseOfferingsTool(_RetrievalTool):
    name = "get_course_offerings"
    description = "Read course offerings for multiple course IDs in one batch."
    parameters = {
        "type": "object",
        "properties": {"course_ids": {"type": "array", "items": {"type": "string"}}},
        "required": ["course_ids"],
        "additionalProperties": False,
    }

    async def execute(self, db: AsyncSession, *, course_ids: list[str]):
        return await self.service.get_course_offerings(db, course_ids=course_ids)


class GetCourseSectionsTool(_RetrievalTool):
    name = "get_course_sections"
    description = "Read open sections for multiple offering IDs in one batch."
    parameters = {
        "type": "object",
        "properties": {"offering_ids": {"type": "array", "items": {"type": "string"}}},
        "required": ["offering_ids"],
        "additionalProperties": False,
    }

    async def execute(self, db: AsyncSession, *, offering_ids: list[str]):
        return await self.service.get_course_sections(db, offering_ids=offering_ids)


class GetSectionMeetingsTool(_RetrievalTool):
    name = "get_section_meetings"
    description = "Read meetings for multiple section IDs in one batch."
    parameters = {
        "type": "object",
        "properties": {"section_ids": {"type": "array", "items": {"type": "string"}}},
        "required": ["section_ids"],
        "additionalProperties": False,
    }

    async def execute(self, db: AsyncSession, *, section_ids: list[str]):
        return await self.service.get_section_meetings(db, section_ids=section_ids)
