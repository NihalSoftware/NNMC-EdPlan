from datetime import datetime

from pydantic import BaseModel, Field


class UniversitySummary(BaseModel):
    university_id: str
    university_name: str
    city: str | None = None
    state: str | None = None
    website: str | None = None


class ProgramSummary(BaseModel):
    program_id: str
    program_name: str
    degree: str
    total_credit_hours: int
    total_credit_hours_text: str | None = None
    total_credit_hours_min: float | None = None
    total_credit_hours_max: float | None = None
    catalog_title: str | None = None
    catalog_url: str | None = None
    catalog_year: str | None = None
    description: str | None = None
    metadata_json: dict | None = None
    official_source_id: str | None = None
    official_source_url: str | None = None
    source_retrieved_at: datetime | None = None
    university: UniversitySummary


class CourseSummary(BaseModel):
    course_id: str
    program_id: str
    course_code: str
    code: str | None = None
    course_name: str
    credits: float
    lecture_hours: float = 0
    lab_hours: float = 0
    recommended_year: int | None = None
    year: int | str | None = None
    recommended_semester: str | None = None
    semester: str | None = None
    is_elective: bool = False
    default_plan_eligible: bool = False
    description: str | None = None
    prerequisite: str | None = None
    corequisite: str | None = None
    pre_or_corequisite: str | None = None
    requirement_expressions: dict = Field(default_factory=dict)
    catalog_url: str | None = None
    credit_text: str | None = None
    credits_min: float | None = None
    credits_max: float | None = None
    requirement_occurrences: list[dict] = Field(default_factory=list)
    metadata_json: dict | None = None
    source_sequence: int | None = None
    official_source_id: str | None = None
    official_source_url: str | None = None
    source_retrieved_at: datetime | None = None


class ProgramDetail(ProgramSummary):
    average_annual_cost: str | None = None
    eligibility_criteria: str | None = None
    courses: list[CourseSummary] = Field(default_factory=list)
    years: list[dict] = Field(default_factory=list)


class ProgramListResponse(BaseModel):
    success: bool
    data: list[ProgramSummary]
    metadata: dict


class ProgramDetailResponse(BaseModel):
    success: bool
    data: ProgramDetail
