from __future__ import annotations

from datetime import time

from pydantic import BaseModel, Field

from app.student.domains.scheduling.schemas.schedulepilot import (
    ScheduleCourse,
    ScheduleMeeting,
    ScheduleSection,
)


class ScheduleConflict(BaseModel):
    conflict_id: str
    type: str
    section_a_id: str | None = None
    section_b_id: str | None = None
    course_a_id: str | None = None
    course_b_id: str | None = None
    weekday: int | None = None
    overlap_start_time: time | None = None
    overlap_end_time: time | None = None
    message: str
    metadata: dict = Field(default_factory=dict)


class ScheduleWarning(BaseModel):
    warning_id: str
    type: str
    section_id: str | None = None
    course_id: str | None = None
    meeting_id: str | None = None
    message: str
    metadata: dict = Field(default_factory=dict)


class ScheduleValidationSummary(BaseModel):
    conflict_count: int = 0
    warning_count: int = 0
    checked_meetings: int = 0
    validation_time_ms: int = 0


class ScheduleMetrics(BaseModel):
    total_credits: float
    earliest_start_time: time | None = None
    latest_end_time: time | None = None
    total_instruction_minutes: int
    total_gap_minutes: int
    average_gap_minutes: float | None = None
    maximum_gap_minutes: int | None = None
    campus_days: int
    monday_classes: int
    tuesday_classes: int
    wednesday_classes: int
    thursday_classes: int
    friday_classes: int
    saturday_classes: int
    sunday_classes: int
    online_section_count: int
    hybrid_section_count: int
    in_person_section_count: int
    asynchronous_section_count: int
    total_sections: int
    open_sections: int
    closed_sections: int
    cancelled_sections: int
    available_seat_count: int | None = None
    total_capacity: int | None = None
    total_enrollment: int | None = None
    open_seat_ratio: float | None = None
    total_meetings: int
    synchronous_meetings: int
    asynchronous_meetings: int
    average_meeting_duration: float | None = None
    longest_meeting_duration: int | None = None
    total_courses: int
    lecture_count: int
    lab_count: int
    discussion_count: int
    other_component_count: int


class ScheduleMetricsSummary(BaseModel):
    computation_time_ms: int = 0
    meeting_count: int = 0
    section_count: int = 0
    metric_version: str = "1.0"


class PreferenceEvaluation(BaseModel):
    preference_key: str
    satisfied: bool
    score_delta: float
    rationale: str


class ScheduleScoringSummary(BaseModel):
    scoring_version: str = "1.0"
    scoring_time_ms: int = 0
    evaluated_preferences: int = 0
    applied_bonus_count: int = 0
    applied_penalty_count: int = 0
    bonus_total: float = 0.0
    penalty_total: float = 0.0
    satisfied_preferences: list[str] = Field(default_factory=list)
    violated_preferences: list[str] = Field(default_factory=list)
    evaluations: list[PreferenceEvaluation] = Field(default_factory=list)


class ScheduleCandidate(BaseModel):
    candidate_id: str
    courses: list[ScheduleCourse]
    sections: list[ScheduleSection]
    meetings: list[ScheduleMeeting]
    conflicts: list[ScheduleConflict] = Field(default_factory=list)
    warnings: list[ScheduleWarning] = Field(default_factory=list)
    is_feasible: bool | None = None
    validation_summary: ScheduleValidationSummary = Field(default_factory=ScheduleValidationSummary)
    metrics: ScheduleMetrics | None = None
    metrics_summary: ScheduleMetricsSummary = Field(default_factory=ScheduleMetricsSummary)
    score: float | None = None
    normalized_score: float | None = None
    scoring_summary: ScheduleScoringSummary = Field(default_factory=ScheduleScoringSummary)
    metadata: dict = Field(default_factory=dict)


class ScheduleOption(BaseModel):
    option_id: str
    rank: int
    score: float | None = None
    normalized_score: float | None = None
    selected_sections: list[ScheduleSection] = Field(default_factory=list)
    selected_meetings: list[ScheduleMeeting] = Field(default_factory=list)
    metrics: ScheduleMetrics | None = None
    warnings: list[ScheduleWarning] = Field(default_factory=list)
    conflicts: list[ScheduleConflict] = Field(default_factory=list)
    explanation: str
    tradeoffs: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class ScheduleGenerationMetadata(BaseModel):
    generated_count: int
    truncated: bool
    generation_time_ms: int
    max_candidate_count: int
    course_count: int
    section_count: int


class ScheduleGenerationResult(BaseModel):
    candidates: list[ScheduleCandidate] = Field(default_factory=list)
    metadata: ScheduleGenerationMetadata
    warnings: list[str] = Field(default_factory=list)


class ScheduleRankingMetadata(BaseModel):
    evaluated_candidates: int
    feasible_candidates: int
    ranked_candidates: int
    returned_candidates: int
    ranking_version: str = "1.0"
    ranking_time_ms: int = 0
    duplicate_candidates_filtered: int = 0
    max_options: int


class ScheduleRankingResult(BaseModel):
    options: list[ScheduleOption] = Field(default_factory=list)
    top_option: ScheduleOption | None = None
    metadata: ScheduleRankingMetadata
