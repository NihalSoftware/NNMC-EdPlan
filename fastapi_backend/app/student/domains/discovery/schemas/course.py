from __future__ import annotations

from pydantic import BaseModel, Field

from app.student.domains.discovery.schemas.program import ProgramSummary


class CourseSummary(BaseModel):
    course_id: str
    program_id: str
    course_code: str
    code: str | None = None
    course_name: str
    name: str | None = None
    credits: int
    lecture_hours: int = 0
    lab_hours: int = 0
    recommended_year: int | None = None
    year: int | str | None = None
    recommended_semester: str | None = None
    semester: str | None = None
    is_elective: bool = False
    default_plan_eligible: bool = False
    prerequisite: str | None = None
    corequisite: str | None = None
    description: str | None = None
    metadata_json: dict | None = None
    source_sequence: int | None = None
    catalog_url: str | None = None
    credit_text: str | None = None
    credits_min: int | None = None
    credits_max: int | None = None
    requirement_occurrences: list[dict] = Field(default_factory=list)


class CoursePrerequisiteResponse(BaseModel):
    id: str
    course_id: str
    prerequisite_course_id: str
    course: CourseSummary


class CourseCorequisiteResponse(BaseModel):
    id: str
    course_id: str
    corequisite_course_id: str
    course: CourseSummary


class CourseDetail(CourseSummary):
    program: ProgramSummary
    prerequisites: list[CoursePrerequisiteResponse] = Field(default_factory=list)
    corequisites: list[CourseCorequisiteResponse] = Field(default_factory=list)


class CourseListResponse(BaseModel):
    success: bool
    data: list[CourseSummary]
    metadata: dict


class CourseDetailResponse(BaseModel):
    success: bool
    data: CourseDetail


class CoursePrerequisiteListResponse(BaseModel):
    success: bool
    data: list[CoursePrerequisiteResponse]
    metadata: dict


class CourseCorequisiteListResponse(BaseModel):
    success: bool
    data: list[CourseCorequisiteResponse]
    metadata: dict
