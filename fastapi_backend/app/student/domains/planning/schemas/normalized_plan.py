from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.student.domains.discovery.schemas.course import CourseSummary
from app.student.domains.discovery.schemas.program import ProgramSummary, UniversitySummary
from app.student.domains.scheduling.schemas.catalog import AcademicTermSummary

PlanCourseStatus = Literal["Planned", "In Progress", "Completed"]


class PlanCreateRequest(BaseModel):
    user_id: int = Field(gt=0)
    university_id: str = Field(min_length=1)
    program_id: str = Field(min_length=1)
    plan_name: str = Field(min_length=1, max_length=160)
    description: str | None = None
    is_active: bool = True


class PlanUpdateRequest(BaseModel):
    plan_name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    is_active: bool | None = None


class PlanCourseCreateRequest(BaseModel):
    course_id: str = Field(min_length=1)
    planned_term_id: str | None = None
    status: PlanCourseStatus = "Planned"
    notes: str | None = None


class PlanCourseUpdateRequest(BaseModel):
    planned_term_id: str | None = None
    status: PlanCourseStatus | None = None
    notes: str | None = None


class TermCreditTotal(BaseModel):
    planned_term_id: str | None = None
    term_name: str | None = None
    credits: float


class PlanCourseSummary(BaseModel):
    id: str
    plan_id: str
    course_id: str
    planned_term_id: str | None = None
    status: PlanCourseStatus
    notes: str | None = None
    course: CourseSummary | None = None
    planned_term: AcademicTermSummary | None = None


class PlanSummary(BaseModel):
    plan_id: str
    user_id: int
    university_id: str
    program_id: str
    plan_name: str
    description: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    university: UniversitySummary | None = None
    program: ProgramSummary | None = None
    max_term_credits: int
    term_credit_totals: list[TermCreditTotal] = Field(default_factory=list)


class PlanDetail(PlanSummary):
    courses: list[PlanCourseSummary] = Field(default_factory=list)


class PlanListResponse(BaseModel):
    success: bool
    data: list[PlanSummary]
    metadata: dict


class PlanDetailResponse(BaseModel):
    success: bool
    data: PlanDetail


class PlanCourseListResponse(BaseModel):
    success: bool
    data: list[PlanCourseSummary]
    metadata: dict


class PlanCourseDetailResponse(BaseModel):
    success: bool
    data: PlanCourseSummary
    metadata: dict


class PlanCourseDeleteResponse(BaseModel):
    success: bool
    data: None = None
    metadata: dict
