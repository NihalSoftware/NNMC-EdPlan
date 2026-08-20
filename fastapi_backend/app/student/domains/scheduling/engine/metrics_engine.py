from __future__ import annotations

from collections import defaultdict
from datetime import time
from time import perf_counter
from typing import TypedDict, cast

from app.student.domains.scheduling.engine.candidate_models import (
    ScheduleCandidate,
    ScheduleMetrics,
    ScheduleMetricsSummary,
)
from app.student.domains.scheduling.schemas.schedulepilot import ScheduleMeeting

WEEKDAY_FIELDS = {
    1: "monday_classes",
    2: "tuesday_classes",
    3: "wednesday_classes",
    4: "thursday_classes",
    5: "friday_classes",
    6: "saturday_classes",
    7: "sunday_classes",
}


class _CapacityMetrics(TypedDict):
    available_seat_count: int | None
    total_capacity: int | None
    total_enrollment: int | None
    open_seat_ratio: float | None


class ScheduleMetricsEngine:
    """Computes objective, deterministic metrics for validated schedule candidates."""

    def compute(self, candidate: ScheduleCandidate) -> ScheduleCandidate:
        started_at = perf_counter()
        metrics = self._metrics(candidate)
        computation_time_ms = max(0, round((perf_counter() - started_at) * 1000))
        return candidate.model_copy(
            update={
                "metrics": metrics,
                "metrics_summary": ScheduleMetricsSummary(
                    computation_time_ms=computation_time_ms,
                    meeting_count=len(candidate.meetings),
                    section_count=len(candidate.sections),
                    metric_version="1.0",
                ),
            },
            deep=True,
        )

    def compute_many(self, candidates: list[ScheduleCandidate]) -> list[ScheduleCandidate]:
        return [self.compute(candidate) for candidate in candidates]

    def _metrics(self, candidate: ScheduleCandidate) -> ScheduleMetrics:
        valid_sync_meetings = [
            meeting for meeting in candidate.meetings if _has_valid_sync_time(meeting)
        ]
        durations = [_duration_minutes(meeting) for meeting in valid_sync_meetings]
        gaps = _gaps_by_weekday(valid_sync_meetings)
        weekday_counts = _weekday_counts(valid_sync_meetings)
        capacity = _capacity_metrics(candidate)
        components = _component_counts(candidate)
        async_section_ids = {
            meeting.section_id for meeting in candidate.meetings if meeting.is_async
        }
        return ScheduleMetrics(
            total_credits=sum(course.credits for course in candidate.courses),
            earliest_start_time=(
                min(cast(time, meeting.start_time) for meeting in valid_sync_meetings)
                if valid_sync_meetings
                else None
            ),
            latest_end_time=(
                max(cast(time, meeting.end_time) for meeting in valid_sync_meetings)
                if valid_sync_meetings
                else None
            ),
            total_instruction_minutes=sum(durations),
            total_gap_minutes=sum(gaps),
            average_gap_minutes=(sum(gaps) / len(gaps) if gaps else None),
            maximum_gap_minutes=(max(gaps) if gaps else None),
            campus_days=len({meeting.weekday for meeting in valid_sync_meetings}),
            monday_classes=weekday_counts[1],
            tuesday_classes=weekday_counts[2],
            wednesday_classes=weekday_counts[3],
            thursday_classes=weekday_counts[4],
            friday_classes=weekday_counts[5],
            saturday_classes=weekday_counts[6],
            sunday_classes=weekday_counts[7],
            online_section_count=len(
                [
                    section
                    for section in candidate.sections
                    if section.instruction_method == "Online"
                ]
            ),
            hybrid_section_count=len(
                [
                    section
                    for section in candidate.sections
                    if section.instruction_method == "Hybrid"
                ]
            ),
            in_person_section_count=len(
                [
                    section
                    for section in candidate.sections
                    if section.instruction_method == "In Person"
                ]
            ),
            asynchronous_section_count=len(async_section_ids),
            total_sections=len(candidate.sections),
            open_sections=len(
                [section for section in candidate.sections if section.status == "Open"]
            ),
            closed_sections=len(
                [section for section in candidate.sections if section.status == "Closed"]
            ),
            cancelled_sections=len(
                [section for section in candidate.sections if section.status == "Cancelled"]
            ),
            available_seat_count=capacity["available_seat_count"],
            total_capacity=capacity["total_capacity"],
            total_enrollment=capacity["total_enrollment"],
            open_seat_ratio=capacity["open_seat_ratio"],
            total_meetings=len(candidate.meetings),
            synchronous_meetings=len(
                [meeting for meeting in candidate.meetings if not meeting.is_async]
            ),
            asynchronous_meetings=len(
                [meeting for meeting in candidate.meetings if meeting.is_async]
            ),
            average_meeting_duration=(sum(durations) / len(durations) if durations else None),
            longest_meeting_duration=(max(durations) if durations else None),
            total_courses=len(candidate.courses),
            lecture_count=components["lecture_count"],
            lab_count=components["lab_count"],
            discussion_count=components["discussion_count"],
            other_component_count=components["other_component_count"],
        )


def _has_valid_sync_time(meeting: ScheduleMeeting) -> bool:
    return (
        not meeting.is_async
        and meeting.weekday is not None
        and meeting.start_time is not None
        and meeting.end_time is not None
        and meeting.start_time < meeting.end_time
    )


def _duration_minutes(meeting: ScheduleMeeting) -> int:
    assert meeting.start_time is not None and meeting.end_time is not None
    return (
        meeting.end_time.hour * 60
        + meeting.end_time.minute
        - meeting.start_time.hour * 60
        - meeting.start_time.minute
    )


def _gaps_by_weekday(meetings: list[ScheduleMeeting]) -> list[int]:
    meetings_by_weekday: dict[int, list[ScheduleMeeting]] = defaultdict(list)
    for meeting in meetings:
        assert meeting.weekday is not None
        meetings_by_weekday[meeting.weekday].append(meeting)

    gaps: list[int] = []
    for weekday_meetings in meetings_by_weekday.values():
        ordered_meetings = sorted(
            weekday_meetings,
            key=lambda item: (item.start_time, item.end_time, item.meeting_id),
        )
        for left, right in zip(ordered_meetings, ordered_meetings[1:], strict=False):
            assert left.end_time is not None and right.start_time is not None
            gap = (
                right.start_time.hour * 60
                + right.start_time.minute
                - left.end_time.hour * 60
                - left.end_time.minute
            )
            if gap > 0:
                gaps.append(gap)
    return gaps


def _weekday_counts(meetings: list[ScheduleMeeting]) -> dict[int, int]:
    counts = dict.fromkeys(WEEKDAY_FIELDS, 0)
    for meeting in meetings:
        assert meeting.weekday is not None
        counts[meeting.weekday] += 1
    return counts


def _capacity_metrics(candidate: ScheduleCandidate) -> _CapacityMetrics:
    if any(
        section.capacity is None or section.enrolled is None or section.available_seats is None
        for section in candidate.sections
    ):
        return {
            "available_seat_count": None,
            "total_capacity": None,
            "total_enrollment": None,
            "open_seat_ratio": None,
        }

    total_capacity = sum(cast(int, section.capacity) for section in candidate.sections)
    total_enrollment = sum(cast(int, section.enrolled) for section in candidate.sections)
    available_seat_count = sum(cast(int, section.available_seats) for section in candidate.sections)
    return {
        "available_seat_count": available_seat_count,
        "total_capacity": total_capacity,
        "total_enrollment": total_enrollment,
        "open_seat_ratio": (available_seat_count / total_capacity if total_capacity > 0 else None),
    }


def _component_counts(candidate: ScheduleCandidate) -> dict[str, int]:
    counts = {
        "lecture_count": 0,
        "lab_count": 0,
        "discussion_count": 0,
        "other_component_count": 0,
    }
    for section in candidate.sections:
        offering_type = (section.offering_type or "").strip().lower()
        if offering_type == "lecture":
            counts["lecture_count"] += 1
        elif offering_type == "lab":
            counts["lab_count"] += 1
        elif offering_type in {"discussion", "recitation"}:
            counts["discussion_count"] += 1
        elif offering_type == "lecture+lab":
            counts["lecture_count"] += 1
            counts["lab_count"] += 1
        else:
            counts["other_component_count"] += 1
    return counts
