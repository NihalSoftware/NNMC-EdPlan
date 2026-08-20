from __future__ import annotations

from datetime import time

from app.student.domains.scheduling.engine.candidate_models import (
    ScheduleCandidate,
    ScheduleConflict,
)
from app.student.domains.scheduling.schemas.schedulepilot import ScheduleMeeting


class ConflictDetector:
    """Deterministic conflict detector for generated schedule candidates."""

    def detect(self, candidate: ScheduleCandidate) -> list[ScheduleConflict]:
        conflicts: list[ScheduleConflict] = []
        conflicts.extend(self._duplicate_sections(candidate, len(conflicts)))
        conflicts.extend(self._duplicate_courses(candidate, len(conflicts)))
        conflicts.extend(self._invalid_meetings(candidate, len(conflicts)))
        conflicts.extend(self._time_overlaps(candidate, len(conflicts)))
        return conflicts

    @staticmethod
    def _duplicate_sections(
        candidate: ScheduleCandidate,
        offset: int,
    ) -> list[ScheduleConflict]:
        conflicts: list[ScheduleConflict] = []
        seen: set[str] = set()
        for section in candidate.sections:
            if section.section_id in seen:
                conflicts.append(
                    ScheduleConflict(
                        conflict_id=_conflict_id(offset + len(conflicts) + 1),
                        type="duplicate_section",
                        section_a_id=section.section_id,
                        section_b_id=section.section_id,
                        course_a_id=section.course_id,
                        course_b_id=section.course_id,
                        message=f"Section {section.section_id} is selected more than once.",
                    )
                )
            seen.add(section.section_id)
        return conflicts

    @staticmethod
    def _duplicate_courses(
        candidate: ScheduleCandidate,
        offset: int,
    ) -> list[ScheduleConflict]:
        conflicts: list[ScheduleConflict] = []
        seen: set[str] = set()
        for course in candidate.courses:
            if course.course_id in seen:
                conflicts.append(
                    ScheduleConflict(
                        conflict_id=_conflict_id(offset + len(conflicts) + 1),
                        type="duplicate_course",
                        course_a_id=course.course_id,
                        course_b_id=course.course_id,
                        message=f"Course {course.course_id} is selected more than once.",
                    )
                )
            seen.add(course.course_id)
        return conflicts

    def _invalid_meetings(
        self,
        candidate: ScheduleCandidate,
        offset: int,
    ) -> list[ScheduleConflict]:
        conflicts: list[ScheduleConflict] = []
        for meeting in sorted(candidate.meetings, key=lambda item: item.meeting_id):
            if meeting.is_async:
                continue
            section = _section_for_meeting(candidate, meeting)
            if meeting.weekday is None or meeting.start_time is None or meeting.end_time is None:
                conflicts.append(
                    ScheduleConflict(
                        conflict_id=_conflict_id(offset + len(conflicts) + 1),
                        type="missing_meeting_information",
                        section_a_id=meeting.section_id,
                        course_a_id=section.course_id if section is not None else None,
                        message=(
                            f"Synchronous meeting {meeting.meeting_id} is missing weekday, "
                            "start time, or end time."
                        ),
                        metadata={"meeting_id": meeting.meeting_id},
                    )
                )
                continue
            if meeting.start_time >= meeting.end_time:
                conflicts.append(
                    ScheduleConflict(
                        conflict_id=_conflict_id(offset + len(conflicts) + 1),
                        type="invalid_meeting_range",
                        section_a_id=meeting.section_id,
                        course_a_id=section.course_id if section is not None else None,
                        weekday=meeting.weekday,
                        overlap_start_time=meeting.start_time,
                        overlap_end_time=meeting.end_time,
                        message=f"Meeting {meeting.meeting_id} has an invalid time range.",
                        metadata={"meeting_id": meeting.meeting_id},
                    )
                )
        return conflicts

    def _time_overlaps(
        self,
        candidate: ScheduleCandidate,
        offset: int,
    ) -> list[ScheduleConflict]:
        conflicts: list[ScheduleConflict] = []
        meetings = sorted(
            [meeting for meeting in candidate.meetings if _has_valid_sync_time(meeting)],
            key=lambda item: (
                item.weekday,
                item.start_time,
                item.end_time,
                item.section_id,
                item.meeting_id,
            ),
        )
        for left_index, left in enumerate(meetings):
            for right in meetings[left_index + 1 :]:
                if left.weekday != right.weekday:
                    continue
                overlap = _overlap(left, right)
                if overlap is None:
                    continue
                left_section = _section_for_meeting(candidate, left)
                right_section = _section_for_meeting(candidate, right)
                conflicts.append(
                    ScheduleConflict(
                        conflict_id=_conflict_id(offset + len(conflicts) + 1),
                        type="time_overlap",
                        section_a_id=left.section_id,
                        section_b_id=right.section_id,
                        course_a_id=left_section.course_id if left_section is not None else None,
                        course_b_id=right_section.course_id if right_section is not None else None,
                        weekday=left.weekday,
                        overlap_start_time=overlap[0],
                        overlap_end_time=overlap[1],
                        message=(
                            f"Sections {left.section_id} and {right.section_id} overlap "
                            f"on weekday {left.weekday}."
                        ),
                        metadata={
                            "meeting_a_id": left.meeting_id,
                            "meeting_b_id": right.meeting_id,
                        },
                    )
                )
        return conflicts


def _has_valid_sync_time(meeting: ScheduleMeeting) -> bool:
    return (
        not meeting.is_async
        and meeting.weekday is not None
        and meeting.start_time is not None
        and meeting.end_time is not None
        and meeting.start_time < meeting.end_time
    )


def _overlap(left: ScheduleMeeting, right: ScheduleMeeting) -> tuple[time, time] | None:
    if (
        left.start_time is None
        or left.end_time is None
        or right.start_time is None
        or right.end_time is None
    ):
        return None
    overlap_start = max(left.start_time, right.start_time)
    overlap_end = min(left.end_time, right.end_time)
    if overlap_start < overlap_end:
        return overlap_start, overlap_end
    return None


def _section_for_meeting(candidate: ScheduleCandidate, meeting: ScheduleMeeting):
    for section in candidate.sections:
        if section.section_id == meeting.section_id:
            return section
    return None


def _conflict_id(index: int) -> str:
    return f"conflict-{index:06d}"
