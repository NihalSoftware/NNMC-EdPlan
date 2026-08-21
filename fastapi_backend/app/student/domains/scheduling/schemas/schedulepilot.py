from __future__ import annotations

from datetime import date, datetime, time

from pydantic import BaseModel, Field


class ScheduleUniversity(BaseModel):
    university_id: str
    university_name: str
    city: str | None = None
    state: str | None = None
    website: str | None = None


class ScheduleProgram(BaseModel):
    program_id: str
    program_name: str
    degree: str
    total_credit_hours: int | None = None


class ScheduleTerm(BaseModel):
    term_id: str
    term_name: str
    start_date: date
    end_date: date
    is_active: bool


class ScheduleStudentPlan(BaseModel):
    plan_id: str
    user_id: int
    university_id: str
    program_id: str
    plan_name: str
    description: str | None = None
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    university: ScheduleUniversity | None = None
    program: ScheduleProgram | None = None


class ScheduleCourse(BaseModel):
    plan_course_id: str
    plan_id: str
    course_id: str
    planned_term_id: str | None = None
    status: str
    notes: str | None = None
    course_code: str
    course_name: str
    credits: float
    lecture_hours: float
    lab_hours: float
    recommended_year: int | None = None
    recommended_semester: str | None = None
    planned_term: ScheduleTerm | None = None


class ScheduleCourseOffering(BaseModel):
    offering_id: str
    course_id: str
    term_id: str
    offering_type: str
    course_code: str
    course_name: str
    credits: float
    term: ScheduleTerm


class ScheduleSection(BaseModel):
    section_id: str
    offering_id: str
    course_id: str
    term_id: str
    offering_type: str | None = None
    section_number: str
    crn: str
    campus: str | None = None
    instructor: str | None = None
    instruction_method: str
    capacity: int | None = None
    enrolled: int | None = None
    available_seats: int | None = None
    status: str


class ScheduleMeeting(BaseModel):
    meeting_id: str
    section_id: str
    weekday: int | None = None
    start_time: time | None = None
    end_time: time | None = None
    building: str | None = None
    room: str | None = None
    meeting_type: str
    is_async: bool


class ScheduleRetrievalWarnings(BaseModel):
    courses_without_offerings: list[str] = Field(default_factory=list)
    offerings_without_sections: list[str] = Field(default_factory=list)
    sections_without_meetings: list[str] = Field(default_factory=list)


class ScheduleRetrievalContext(BaseModel):
    plan: ScheduleStudentPlan
    courses: list[ScheduleCourse] = Field(default_factory=list)
    terms: list[ScheduleTerm] = Field(default_factory=list)
    offerings: list[ScheduleCourseOffering] = Field(default_factory=list)
    sections: list[ScheduleSection] = Field(default_factory=list)
    meetings: list[ScheduleMeeting] = Field(default_factory=list)
    warnings: ScheduleRetrievalWarnings = Field(default_factory=ScheduleRetrievalWarnings)
