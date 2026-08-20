from __future__ import annotations

from datetime import time

from app.student.domains.scheduling.engine import (
    ConflictDetector,
    FeasibilityValidator,
    ScheduleCandidate,
)
from app.student.domains.scheduling.schemas.schedulepilot import (
    ScheduleCourse,
    ScheduleMeeting,
    ScheduleSection,
)


def _course(course_id: str = "course-a") -> ScheduleCourse:
    return ScheduleCourse(
        plan_course_id=f"pc-{course_id}",
        plan_id="plan-1",
        course_id=course_id,
        status="Planned",
        course_code=course_id.upper(),
        course_name=f"{course_id} Name",
        credits=3,
        lecture_hours=3,
        lab_hours=0,
    )


def _section(
    section_id: str,
    course_id: str,
    *,
    instructor: str | None = "Ada Lovelace",
    room_status: str = "Open",
    instruction_method: str = "In Person",
) -> ScheduleSection:
    return ScheduleSection(
        section_id=section_id,
        offering_id=f"offering-{section_id}",
        course_id=course_id,
        term_id="term-1",
        section_number=section_id,
        crn=f"crn-{section_id}",
        instructor=instructor,
        instruction_method=instruction_method,
        capacity=30,
        enrolled=10,
        available_seats=20,
        status=room_status,
    )


def _meeting(
    meeting_id: str,
    section_id: str,
    *,
    weekday: int | None = 1,
    start_time: time | None = time(9, 0),
    end_time: time | None = time(10, 0),
    room: str | None = "101",
    meeting_type: str = "Class",
    is_async: bool = False,
) -> ScheduleMeeting:
    return ScheduleMeeting(
        meeting_id=meeting_id,
        section_id=section_id,
        weekday=weekday,
        start_time=start_time,
        end_time=end_time,
        building="SCI",
        room=room,
        meeting_type=meeting_type,
        is_async=is_async,
    )


def _candidate(courses=None, sections=None, meetings=None) -> ScheduleCandidate:
    return ScheduleCandidate(
        candidate_id="candidate-000001",
        courses=courses or [_course("course-a")],
        sections=sections or [_section("section-a", "course-a")],
        meetings=meetings or [_meeting("meeting-a", "section-a")],
    )


def test_conflict_detector_detects_overlapping_meetings():
    candidate = _candidate(
        courses=[_course("course-a"), _course("course-b")],
        sections=[
            _section("section-a", "course-a"),
            _section("section-b", "course-b"),
        ],
        meetings=[
            _meeting("meeting-a", "section-a", start_time=time(9, 0), end_time=time(10, 15)),
            _meeting("meeting-b", "section-b", start_time=time(10, 0), end_time=time(11, 0)),
        ],
    )

    conflicts = ConflictDetector().detect(candidate)

    assert [conflict.type for conflict in conflicts] == ["time_overlap"]
    assert conflicts[0].conflict_id == "conflict-000001"
    assert conflicts[0].overlap_start_time == time(10, 0)
    assert conflicts[0].overlap_end_time == time(10, 15)
    assert conflicts[0].course_a_id == "course-a"
    assert conflicts[0].course_b_id == "course-b"


def test_adjacent_meetings_and_different_weekdays_are_not_conflicts():
    adjacent = _candidate(
        courses=[_course("course-a"), _course("course-b")],
        sections=[_section("section-a", "course-a"), _section("section-b", "course-b")],
        meetings=[
            _meeting("meeting-a", "section-a", start_time=time(9, 0), end_time=time(10, 0)),
            _meeting("meeting-b", "section-b", start_time=time(10, 0), end_time=time(11, 0)),
        ],
    )
    different_day = _candidate(
        courses=[_course("course-a"), _course("course-b")],
        sections=[_section("section-a", "course-a"), _section("section-b", "course-b")],
        meetings=[
            _meeting("meeting-a", "section-a", weekday=1),
            _meeting("meeting-b", "section-b", weekday=2),
        ],
    )

    assert ConflictDetector().detect(adjacent) == []
    assert ConflictDetector().detect(different_day) == []


def test_async_sections_do_not_create_missing_time_conflicts():
    candidate = _candidate(
        meetings=[
            _meeting(
                "meeting-a",
                "section-a",
                weekday=None,
                start_time=None,
                end_time=None,
                meeting_type="Online Async",
                is_async=True,
            )
        ]
    )

    validated = FeasibilityValidator().validate(candidate)

    assert validated.conflicts == []
    assert validated.is_feasible is True


def test_detector_flags_duplicate_sections_and_courses():
    course = _course("course-a")
    section = _section("section-a", "course-a")
    candidate = _candidate(
        courses=[course, course],
        sections=[section, section],
        meetings=[],
    )

    conflicts = ConflictDetector().detect(candidate)

    assert [conflict.type for conflict in conflicts] == [
        "duplicate_section",
        "duplicate_course",
    ]


def test_detector_flags_malformed_synchronous_meeting_times():
    missing = _candidate(
        meetings=[
            _meeting("meeting-a", "section-a", weekday=1, start_time=None, end_time=time(10, 0))
        ]
    )
    invalid = _candidate(
        meetings=[_meeting("meeting-a", "section-a", start_time=time(10, 0), end_time=time(10, 0))]
    )

    assert [conflict.type for conflict in ConflictDetector().detect(missing)] == [
        "missing_meeting_information"
    ]
    assert [conflict.type for conflict in ConflictDetector().detect(invalid)] == [
        "invalid_meeting_range"
    ]


def test_validator_generates_warnings_without_invalidating_candidate():
    candidate = _candidate(
        sections=[
            _section(
                "section-a",
                "course-a",
                instructor=None,
                room_status="Closed",
                instruction_method="Telepathy",
            )
        ],
        meetings=[
            _meeting(
                "meeting-a",
                "section-a",
                start_time=time(8, 0),
                end_time=time(12, 30),
                room=None,
            )
        ],
    )

    validated = FeasibilityValidator().validate(candidate)

    assert validated.is_feasible is True
    assert [warning.type for warning in validated.warnings] == [
        "missing_instructor",
        "closed_section",
        "unknown_instruction_method",
        "missing_room",
        "long_meeting",
    ]
    assert validated.validation_summary.conflict_count == 0
    assert validated.validation_summary.warning_count == 5
    assert validated.validation_summary.checked_meetings == 1


def test_validator_marks_candidate_infeasible_when_conflicts_exist():
    candidate = _candidate(
        courses=[_course("course-a"), _course("course-b")],
        sections=[_section("section-a", "course-a"), _section("section-b", "course-b")],
        meetings=[
            _meeting("meeting-a", "section-a", start_time=time(9, 0), end_time=time(10, 15)),
            _meeting("meeting-b", "section-b", start_time=time(10, 0), end_time=time(11, 0)),
        ],
    )

    validated = FeasibilityValidator().validate(candidate)

    assert validated.is_feasible is False
    assert validated.validation_summary.conflict_count == 1
    assert validated.validation_summary.warning_count == 0
