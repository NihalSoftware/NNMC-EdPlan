from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.student.domains.discovery.services.course_service import CourseService
    from app.student.domains.discovery.services.program_service import ProgramService
    from app.student.domains.planning.services.graduation_audit_service import (
        GraduationAuditService,
    )
    from app.student.domains.scheduling.services.catalog_service import TermService


def _course_service():
    from app.student.domains.discovery.services.course_service import course_service

    return course_service


def _program_service():
    from app.student.domains.discovery.services.program_service import program_service

    return program_service


def _audit_service():
    from app.student.domains.planning.services.graduation_audit_service import (
        graduation_audit_service,
    )

    return graduation_audit_service


def _term_service():
    from app.student.domains.scheduling.services.catalog_service import term_service

    return term_service


class GetRemainingCoursesTool:
    name = "get_remaining_courses"
    description = (
        "Read the courses still missing from a student's plan audit. Input: plan_id. "
        "Output: audit-derived missing courses and remaining credit/course counts. Use "
        "when the student asks what is left, whether graduation is possible, or how to "
        "accelerate graduation."
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
        audit = await (self.service or _audit_service()).get_audit(db, plan_id)
        return {
            "plan_id": audit.get("plan_id"),
            "graduation_ready": audit.get("graduation_ready"),
            "credits": audit.get("credits"),
            "courses": audit.get("courses"),
            "remaining_courses": audit.get("missing_courses", []),
        }


class GetCourseDetailsTool:
    name = "get_course_details"
    description = (
        "Read catalog details for one course. Input: course_id. Output: course code, "
        "name, credits, recommended term metadata, and any embedded prerequisite or "
        "corequisite details. Use before advising about a specific course."
    )
    parameters = {
        "type": "object",
        "properties": {"course_id": {"type": "string"}},
        "required": ["course_id"],
        "additionalProperties": False,
    }

    def __init__(self, service: CourseService | None = None) -> None:
        self.service = service

    async def execute(self, db: AsyncSession, course_id: str) -> dict:
        return await (self.service or _course_service()).get_course_by_id(db, course_id)


class GetPrerequisitesTool:
    name = "get_prerequisites"
    description = (
        "Read prerequisite courses for a catalog course. Input: course_id. Output: "
        "prerequisite course links and course summaries. Use before recommending a "
        "course order or accelerated plan."
    )
    parameters = {
        "type": "object",
        "properties": {"course_id": {"type": "string"}},
        "required": ["course_id"],
        "additionalProperties": False,
    }

    def __init__(self, service: CourseService | None = None) -> None:
        self.service = service

    async def execute(self, db: AsyncSession, course_id: str) -> list[dict]:
        return await (self.service or _course_service()).list_prerequisites(db, course_id)


class GetCorequisitesTool:
    name = "get_corequisites"
    description = (
        "Read corequisite courses for a catalog course. Input: course_id. Output: "
        "corequisite course links and course summaries. Use before recommending "
        "same-term course combinations."
    )
    parameters = {
        "type": "object",
        "properties": {"course_id": {"type": "string"}},
        "required": ["course_id"],
        "additionalProperties": False,
    }

    def __init__(self, service: CourseService | None = None) -> None:
        self.service = service

    async def execute(self, db: AsyncSession, course_id: str) -> list[dict]:
        return await (self.service or _course_service()).list_corequisites(db, course_id)


class GetProgramRequirementsTool:
    name = "get_program_requirements"
    description = (
        "Read degree/program requirements from the catalog. Input: program_id. Output: "
        "program metadata, total required credits, required courses, and recommended "
        "year/semester grouping when available. Use before generating candidate plans."
    )
    parameters = {
        "type": "object",
        "properties": {"program_id": {"type": "string"}},
        "required": ["program_id"],
        "additionalProperties": False,
    }

    def __init__(self, service: ProgramService | None = None) -> None:
        self.service = service

    async def execute(self, db: AsyncSession, program_id: str) -> dict:
        return await (self.service or _program_service()).get_program_by_id(db, program_id)


class GetAvailableTermsTool:
    name = "get_available_terms"
    description = (
        "Read active academic terms available for planning. Input: none. Output: term "
        "IDs, names, dates, and active status. Use when assigning courses to future "
        "semesters or comparing plan timelines."
    )
    parameters = {
        "type": "object",
        "properties": {},
        "additionalProperties": False,
    }

    def __init__(self, service: TermService | None = None) -> None:
        self.service = service

    async def execute(self, db: AsyncSession) -> list[dict]:
        return await (self.service or _term_service()).list_terms(db)
