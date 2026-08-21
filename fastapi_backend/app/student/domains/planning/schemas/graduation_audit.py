from __future__ import annotations

from pydantic import BaseModel, Field


class GraduationAuditProgram(BaseModel):
    program_id: str
    program_name: str
    degree: str
    required_credits: int


class GraduationAuditCredits(BaseModel):
    planned: float
    required: float
    remaining: float
    completion_percentage: float


class GraduationAuditCourses(BaseModel):
    total_required: int
    completed: int
    missing: int
    completion_percentage: float


class GraduationAuditCourseSummary(BaseModel):
    course_id: str
    course_code: str
    course_name: str


class GraduationAuditResult(BaseModel):
    plan_id: str
    program: GraduationAuditProgram
    credits: GraduationAuditCredits
    courses: GraduationAuditCourses
    graduation_ready: bool
    missing_courses: list[GraduationAuditCourseSummary] = Field(default_factory=list)
