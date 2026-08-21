from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.student.domains.scheduling.engine import ScheduleOption


class SaveScheduleRequest(BaseModel):
    user_id: int
    plan_id: str
    selected_option: ScheduleOption
    schedule_name: str | None = None
    notes: str | None = None
    confirmed: bool = False


class ActivationRequest(BaseModel):
    user_id: int
    plan_id: str
    schedule_id: str
    confirmed: bool = False


class DeleteScheduleRequest(BaseModel):
    user_id: int
    plan_id: str
    schedule_id: str
    confirmed: bool = False


class ScheduleSummary(BaseModel):
    schedule_id: str
    plan_id: str
    schedule_name: str | None = None
    status: str
    is_active: bool = False
    is_favorite: bool = False
    total_credits: float
    notes: str | None = None
    generated_at: datetime | None = None
    selected_section_ids: list[str] = Field(default_factory=list)


class SavedScheduleSectionDetail(BaseModel):
    id: str
    schedule_id: str
    section_id: str
    display_order: int
    course_id_snapshot: str | None = None
    section_number_snapshot: str | None = None
    crn_snapshot: str | None = None
    instruction_method_snapshot: str | None = None
    meeting_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    notes: str | None = None
    created_at: datetime | None = None


class SavedScheduleDetail(BaseModel):
    schedule_id: str
    plan_id: str
    parent_schedule_id: str | None = None
    selected_term_id: str | None = None
    schedule_name: str | None = None
    status: str
    source: str
    is_active: bool
    is_favorite: bool
    total_credits: float
    score: float | None = None
    normalized_score: float | None = None
    rank_at_generation: int | None = None
    metrics_snapshot: dict[str, Any] = Field(default_factory=dict)
    conflicts_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    warnings_snapshot: list[dict[str, Any]] = Field(default_factory=list)
    tradeoffs_snapshot: list[Any] = Field(default_factory=list)
    explanation_snapshot: dict[str, Any] = Field(default_factory=dict)
    generation_metadata: dict[str, Any] = Field(default_factory=dict)
    selected_sections: list[SavedScheduleSectionDetail] = Field(default_factory=list)
    selected_section_ids: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None
    deleted_at: datetime | None = None


class SaveScheduleResult(BaseModel):
    success: bool
    schedule: ScheduleSummary


class ActivationResult(BaseModel):
    success: bool
    activated_schedule: ScheduleSummary
    deactivated_schedule_ids: list[str] = Field(default_factory=list)


class DeleteScheduleResult(BaseModel):
    success: bool
    deleted_schedule_id: str
    removed_section_ids: list[str] = Field(default_factory=list)
