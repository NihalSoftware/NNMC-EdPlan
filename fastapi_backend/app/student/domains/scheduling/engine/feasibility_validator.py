from __future__ import annotations

from time import perf_counter

from app.student.domains.scheduling.engine.candidate_models import (
    ScheduleCandidate,
    ScheduleValidationSummary,
    ScheduleWarning,
)
from app.student.domains.scheduling.engine.conflict_detector import ConflictDetector
from app.student.domains.scheduling.schemas.schedulepilot import ScheduleMeeting, ScheduleSection

KNOWN_INSTRUCTION_METHODS = {"In Person", "Online", "Hybrid"}
LONG_MEETING_MINUTES = 180


class FeasibilityValidator:
    """Adds deterministic feasibility analysis to generated candidates."""

    def __init__(self, conflict_detector: ConflictDetector | None = None) -> None:
        self.conflict_detector = conflict_detector or ConflictDetector()

    def validate(self, candidate: ScheduleCandidate) -> ScheduleCandidate:
        started_at = perf_counter()
        conflicts = self.conflict_detector.detect(candidate)
        warnings = self._warnings(candidate)
        validation_time_ms = max(0, round((perf_counter() - started_at) * 1000))
        return candidate.model_copy(
            update={
                "conflicts": conflicts,
                "warnings": warnings,
                "is_feasible": len(conflicts) == 0,
                "validation_summary": ScheduleValidationSummary(
                    conflict_count=len(conflicts),
                    warning_count=len(warnings),
                    checked_meetings=len(candidate.meetings),
                    validation_time_ms=validation_time_ms,
                ),
            },
            deep=True,
        )

    def validate_many(self, candidates: list[ScheduleCandidate]) -> list[ScheduleCandidate]:
        return [self.validate(candidate) for candidate in candidates]

    def _warnings(self, candidate: ScheduleCandidate) -> list[ScheduleWarning]:
        warnings: list[ScheduleWarning] = []
        for section in sorted(candidate.sections, key=lambda item: item.section_id):
            warnings.extend(self._section_warnings(section, len(warnings)))
        for meeting in sorted(candidate.meetings, key=lambda item: item.meeting_id):
            warnings.extend(self._meeting_warnings(meeting, len(warnings)))
        return warnings

    @staticmethod
    def _section_warnings(section: ScheduleSection, offset: int) -> list[ScheduleWarning]:
        warnings: list[ScheduleWarning] = []
        if not section.instructor:
            warnings.append(
                ScheduleWarning(
                    warning_id=_warning_id(offset + len(warnings) + 1),
                    type="missing_instructor",
                    section_id=section.section_id,
                    course_id=section.course_id,
                    message=f"Section {section.section_id} does not list an instructor.",
                )
            )
        if section.status != "Open":
            warnings.append(
                ScheduleWarning(
                    warning_id=_warning_id(offset + len(warnings) + 1),
                    type="closed_section",
                    section_id=section.section_id,
                    course_id=section.course_id,
                    message=f"Section {section.section_id} has status {section.status}.",
                    metadata={"status": section.status},
                )
            )
        if section.instruction_method not in KNOWN_INSTRUCTION_METHODS:
            warnings.append(
                ScheduleWarning(
                    warning_id=_warning_id(offset + len(warnings) + 1),
                    type="unknown_instruction_method",
                    section_id=section.section_id,
                    course_id=section.course_id,
                    message=(
                        f"Section {section.section_id} has unknown instruction method "
                        f"{section.instruction_method}."
                    ),
                    metadata={"instruction_method": section.instruction_method},
                )
            )
        return warnings

    @staticmethod
    def _meeting_warnings(meeting: ScheduleMeeting, offset: int) -> list[ScheduleWarning]:
        warnings: list[ScheduleWarning] = []
        if not meeting.is_async and not meeting.room:
            warnings.append(
                ScheduleWarning(
                    warning_id=_warning_id(offset + len(warnings) + 1),
                    type="missing_room",
                    section_id=meeting.section_id,
                    meeting_id=meeting.meeting_id,
                    message=f"Meeting {meeting.meeting_id} does not list a room.",
                )
            )
        if meeting.is_async and (
            meeting.weekday is not None
            or meeting.start_time is not None
            or meeting.end_time is not None
        ):
            warnings.append(
                ScheduleWarning(
                    warning_id=_warning_id(offset + len(warnings) + 1),
                    type="incomplete_meeting_metadata",
                    section_id=meeting.section_id,
                    meeting_id=meeting.meeting_id,
                    message=f"Async meeting {meeting.meeting_id} includes partial time metadata.",
                )
            )
        if (
            meeting.start_time is not None
            and meeting.end_time is not None
            and meeting.start_time < meeting.end_time
            and _duration_minutes(meeting) > LONG_MEETING_MINUTES
        ):
            warnings.append(
                ScheduleWarning(
                    warning_id=_warning_id(offset + len(warnings) + 1),
                    type="long_meeting",
                    section_id=meeting.section_id,
                    meeting_id=meeting.meeting_id,
                    message=f"Meeting {meeting.meeting_id} is unusually long.",
                    metadata={"duration_minutes": _duration_minutes(meeting)},
                )
            )
        return warnings


def _duration_minutes(meeting: ScheduleMeeting) -> int:
    assert meeting.start_time is not None and meeting.end_time is not None
    start_minutes = meeting.start_time.hour * 60 + meeting.start_time.minute
    end_minutes = meeting.end_time.hour * 60 + meeting.end_time.minute
    return end_minutes - start_minutes


def _warning_id(index: int) -> str:
    return f"warning-{index:06d}"
