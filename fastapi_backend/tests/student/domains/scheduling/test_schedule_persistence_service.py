from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, time
from types import SimpleNamespace

import pytest

from app.student.domains.scheduling.engine import ScheduleMetrics, ScheduleOption
from app.student.domains.scheduling.schemas.schedule_persistence import (
    ActivationRequest,
    DeleteScheduleRequest,
    SaveScheduleRequest,
)
from app.student.domains.scheduling.schemas.schedulepilot import ScheduleMeeting, ScheduleSection
from app.student.domains.scheduling.services.schedule_persistence_service import (
    SchedulePersistenceService,
)


class _Session:
    def __init__(self):
        self.commit_count = 0
        self.rollback_count = 0

    async def commit(self):
        self.commit_count += 1

    async def rollback(self):
        self.rollback_count += 1


class _Repository:
    def __init__(self, *, plan=None, sections=None, schedule=None, active_schedule=None):
        self.plan = plan
        self.sections = sections or []
        self.schedule = schedule
        self.active_schedule = active_schedule
        self.created_schedule = None
        self.replaced_sections = []
        self.deleted_schedule = None
        self.deleted_selected_sections = False
        self.deleted_section_calls = 0
        self.list_schedule_sections_calls = 0

    async def get_plan(self, db, *, plan_id):
        return self.plan

    async def get_sections_by_ids(self, db, *, section_ids):
        return self.sections

    async def get_section_snapshots_by_ids(self, db, *, section_ids):
        existing_ids = {str(section.section_id) for section in self.sections}
        return [
            {
                "section_id": str(section_id),
                "course_id_snapshot": str(uuid.uuid4()),
                "section_number_snapshot": "001",
                "crn_snapshot": "12345",
                "instruction_method_snapshot": "In Person",
            }
            for section_id in section_ids
            if str(section_id) in existing_ids
        ]

    async def create_schedule(
        self,
        db,
        *,
        plan_id,
        total_credits,
        status="Draft",
        schedule_name=None,
        source="system_generated",
        score=None,
        normalized_score=None,
        rank_at_generation=None,
        selected_term_id=None,
        metrics_snapshot=None,
        conflicts_snapshot=None,
        warnings_snapshot=None,
        tradeoffs_snapshot=None,
        explanation_snapshot=None,
        generation_metadata=None,
    ):
        self.created_schedule = SimpleNamespace(
            schedule_id=uuid.uuid4(),
            plan_id=uuid.UUID(str(plan_id)),
            created_at=datetime(2026, 6, 1, 9, 0),
            total_credits=total_credits,
            status=status,
            schedule_name=schedule_name,
            source=source,
            score=score,
            normalized_score=normalized_score,
            rank_at_generation=rank_at_generation,
            selected_term_id=uuid.UUID(str(selected_term_id)) if selected_term_id else None,
            is_active=False,
            is_favorite=False,
            metrics_snapshot=metrics_snapshot or {},
            conflicts_snapshot=conflicts_snapshot or [],
            warnings_snapshot=warnings_snapshot or [],
            tradeoffs_snapshot=tradeoffs_snapshot or [],
            explanation_snapshot=explanation_snapshot or {},
            generation_metadata=generation_metadata or {},
            updated_at=datetime(2026, 6, 1, 9, 0),
            archived_at=None,
            deleted_at=None,
        )
        return self.created_schedule

    async def replace_schedule_sections(self, db, *, schedule_id, sections, notes=None):
        self.replaced_sections = [
            SimpleNamespace(
                schedule_id=uuid.UUID(str(schedule_id)),
                section_id=uuid.UUID(str(section["section_id"])),
                meeting_snapshot=section.get("meeting_snapshot") or [],
            )
            for section in sections
        ]
        return self.replaced_sections

    async def get_schedule(self, db, *, schedule_id):
        return self.schedule

    async def deactivate_plan_schedules(self, db, *, plan_id, except_schedule_id=None):
        if self.active_schedule is None:
            return []
        if str(self.active_schedule.schedule_id) == str(except_schedule_id):
            return []
        self.active_schedule.is_active = False
        self.active_schedule.status = "Archived"
        return [self.active_schedule]

    async def activate_schedule(self, schedule):
        schedule.is_active = True
        schedule.status = "Active"
        return schedule

    async def archive_schedule(self, schedule):
        schedule.is_active = False
        schedule.status = "Archived"
        return schedule

    async def list_schedule_sections(self, db, *, schedule_id):
        self.list_schedule_sections_calls += 1
        return list(self.replaced_sections)

    async def list_schedules_with_sections(self, db, *, plan_id):
        schedules = [self.schedule] if self.schedule is not None else []
        return schedules, {
            schedule.schedule_id: list(self.replaced_sections) for schedule in schedules
        }

    async def get_schedule_with_sections(self, db, *, schedule_id):
        return self.schedule, list(self.replaced_sections)

    async def delete_schedule_sections(self, db, *, schedule_id):
        self.deleted_selected_sections = True
        self.deleted_section_calls += 1

    async def delete_schedule(self, db, schedule):
        self.deleted_schedule = schedule

    async def list_schedules(self, db, *, plan_id):
        return [self.schedule] if self.schedule is not None else []


def _metrics() -> ScheduleMetrics:
    return ScheduleMetrics(
        total_credits=3,
        earliest_start_time=time(9, 0),
        latest_end_time=time(10, 0),
        total_instruction_minutes=60,
        total_gap_minutes=0,
        average_gap_minutes=0.0,
        maximum_gap_minutes=0,
        campus_days=1,
        monday_classes=1,
        tuesday_classes=0,
        wednesday_classes=0,
        thursday_classes=0,
        friday_classes=0,
        saturday_classes=0,
        sunday_classes=0,
        online_section_count=0,
        hybrid_section_count=0,
        in_person_section_count=1,
        asynchronous_section_count=0,
        total_sections=1,
        open_sections=1,
        closed_sections=0,
        cancelled_sections=0,
        available_seat_count=10,
        total_capacity=20,
        total_enrollment=10,
        open_seat_ratio=0.5,
        total_meetings=1,
        synchronous_meetings=1,
        asynchronous_meetings=0,
        average_meeting_duration=60,
        longest_meeting_duration=60,
        total_courses=1,
        lecture_count=1,
        lab_count=0,
        discussion_count=0,
        other_component_count=0,
    )


def _section(section_id: uuid.UUID) -> ScheduleSection:
    term_id = uuid.uuid4()
    return ScheduleSection(
        section_id=str(section_id),
        offering_id=str(uuid.uuid4()),
        course_id=str(uuid.uuid4()),
        term_id=str(term_id),
        offering_type="Lecture",
        section_number="001",
        crn="12345",
        instruction_method="In Person",
        capacity=20,
        enrolled=10,
        available_seats=10,
        status="Open",
    )


def _option(section_id: uuid.UUID) -> ScheduleOption:
    return ScheduleOption(
        option_id="schedule-option-000001",
        rank=1,
        score=80,
        normalized_score=80,
        selected_sections=[_section(section_id)],
        selected_meetings=[
            ScheduleMeeting(
                meeting_id=str(uuid.uuid4()),
                section_id=str(section_id),
                weekday=1,
                start_time=time(9, 0),
                end_time=time(10, 0),
                meeting_type="Class",
                is_async=False,
            )
        ],
        metrics=_metrics(),
        explanation="Rule-based option.",
    )


def _plan(plan_id: uuid.UUID, user_id: int = 1):
    return SimpleNamespace(plan_id=plan_id, user_id=user_id)


def _schedule(plan_id: uuid.UUID, *, status="Final"):
    return SimpleNamespace(
        schedule_id=uuid.uuid4(),
        plan_id=plan_id,
        parent_schedule_id=None,
        selected_term_id=uuid.uuid4(),
        created_at=datetime(2026, 6, 1, 9, 0),
        updated_at=datetime(2026, 6, 1, 9, 0),
        archived_at=None,
        deleted_at=None,
        total_credits=3,
        status=status,
        schedule_name="Best Option",
        source="user_created",
        is_active=status == "Active",
        is_favorite=False,
        score=80,
        normalized_score=80,
        rank_at_generation=1,
        metrics_snapshot={"total_credits": 3},
        conflicts_snapshot=[],
        warnings_snapshot=[],
        tradeoffs_snapshot=["High seat availability"],
        explanation_snapshot={"content": "Rule-based option.", "source": "rule_based"},
        generation_metadata={"notes": "Saved schedule", "source_option_id": "option-1"},
    )


def test_service_saves_schedule_and_replaces_selected_sections_atomically():
    plan_id = uuid.uuid4()
    section_id = uuid.uuid4()
    repository = _Repository(
        plan=_plan(plan_id),
        sections=[SimpleNamespace(section_id=section_id)],
    )
    session = _Session()
    request = SaveScheduleRequest(
        user_id=1,
        plan_id=str(plan_id),
        selected_option=_option(section_id),
        schedule_name="Best Option",
        notes="Student approved.",
        confirmed=True,
    )

    result = asyncio.run(
        SchedulePersistenceService(repository=repository).save_schedule(session, request)
    )

    assert result.success is True
    assert result.schedule.status == "Final"
    assert result.schedule.total_credits == 3
    assert result.schedule.notes == "Student approved."
    assert result.schedule.selected_section_ids == [str(section_id)]
    assert repository.created_schedule is not None
    assert repository.created_schedule.schedule_name == "Best Option"
    assert repository.created_schedule.source == "user_created"
    assert repository.created_schedule.normalized_score == 80
    assert repository.created_schedule.selected_term_id is not None
    assert repository.created_schedule.metrics_snapshot["total_credits"] == 3
    assert repository.created_schedule.tradeoffs_snapshot == []
    assert repository.created_schedule.explanation_snapshot["content"] == "Rule-based option."
    assert repository.replaced_sections[0].section_id == section_id
    assert repository.replaced_sections[0].meeting_snapshot[0]["section_id"] == str(section_id)
    assert session.commit_count == 1
    assert session.rollback_count == 0


def test_service_rejects_missing_plan_and_rolls_back():
    section_id = uuid.uuid4()
    session = _Session()
    request = SaveScheduleRequest(
        user_id=1,
        plan_id=str(uuid.uuid4()),
        selected_option=_option(section_id),
    )

    with pytest.raises(ValueError, match="Plan not found"):
        asyncio.run(
            SchedulePersistenceService(repository=_Repository()).save_schedule(
                session,
                request,
            )
        )

    assert session.commit_count == 0
    assert session.rollback_count == 1


def test_service_rejects_cross_user_plan_access():
    plan_id = uuid.uuid4()
    section_id = uuid.uuid4()
    session = _Session()
    repository = _Repository(
        plan=_plan(plan_id, user_id=2),
        sections=[SimpleNamespace(section_id=section_id)],
    )
    request = SaveScheduleRequest(
        user_id=1,
        plan_id=str(plan_id),
        selected_option=_option(section_id),
    )

    with pytest.raises(PermissionError, match="Plan does not belong"):
        asyncio.run(
            SchedulePersistenceService(repository=repository).save_schedule(session, request)
        )

    assert session.rollback_count == 1


def test_service_rejects_missing_selected_sections():
    plan_id = uuid.uuid4()
    section_id = uuid.uuid4()
    session = _Session()
    repository = _Repository(plan=_plan(plan_id), sections=[])
    request = SaveScheduleRequest(
        user_id=1,
        plan_id=str(plan_id),
        selected_option=_option(section_id),
    )

    with pytest.raises(ValueError, match="Selected sections do not exist"):
        asyncio.run(
            SchedulePersistenceService(repository=repository).save_schedule(session, request)
        )

    assert repository.created_schedule is None
    assert session.rollback_count == 1


def test_service_activates_schedule_and_deactivates_previous_active_schedule():
    plan_id = uuid.uuid4()
    target = _schedule(plan_id)
    active = _schedule(plan_id, status="Active")
    section_id = uuid.uuid4()
    repository = _Repository(plan=_plan(plan_id), schedule=target, active_schedule=active)
    repository.replaced_sections = [SimpleNamespace(section_id=section_id)]
    session = _Session()
    request = ActivationRequest(
        user_id=1,
        plan_id=str(plan_id),
        schedule_id=str(target.schedule_id),
        confirmed=True,
    )

    result = asyncio.run(
        SchedulePersistenceService(repository=repository).activate_schedule(
            session,
            request,
        )
    )

    assert result.success is True
    assert result.activated_schedule.status == "Active"
    assert result.activated_schedule.selected_section_ids == [str(section_id)]
    assert result.activated_schedule.selected_section_ids == [str(section_id)]
    assert result.deactivated_schedule_ids == [str(active.schedule_id)]
    assert active.status == "Archived"
    assert active.is_active is False
    assert target.is_active is True
    assert session.commit_count == 1


def test_service_rejects_duplicate_activation_without_confirmation():
    plan_id = uuid.uuid4()
    target = _schedule(plan_id)
    session = _Session()
    request = ActivationRequest(
        user_id=1,
        plan_id=str(plan_id),
        schedule_id=str(target.schedule_id),
        confirmed=False,
    )

    with pytest.raises(ValueError, match="activation requires confirmation"):
        asyncio.run(
            SchedulePersistenceService(
                repository=_Repository(plan=_plan(plan_id), schedule=target)
            ).activate_schedule(session, request)
        )

    assert target.status == "Final"
    assert session.rollback_count == 1


def test_service_rejects_missing_schedule():
    plan_id = uuid.uuid4()
    session = _Session()
    request = ActivationRequest(
        user_id=1,
        plan_id=str(plan_id),
        schedule_id=str(uuid.uuid4()),
        confirmed=True,
    )

    with pytest.raises(ValueError, match="Schedule not found"):
        asyncio.run(
            SchedulePersistenceService(
                repository=_Repository(plan=_plan(plan_id))
            ).activate_schedule(
                session,
                request,
            )
        )

    assert session.rollback_count == 1


def test_service_deletes_schedule_and_current_plan_sections():
    plan_id = uuid.uuid4()
    schedule = _schedule(plan_id)
    section_id = uuid.uuid4()
    repository = _Repository(plan=_plan(plan_id), schedule=schedule)
    repository.replaced_sections = [SimpleNamespace(section_id=section_id)]
    session = _Session()
    request = DeleteScheduleRequest(
        user_id=1,
        plan_id=str(plan_id),
        schedule_id=str(schedule.schedule_id),
        confirmed=True,
    )

    result = asyncio.run(
        SchedulePersistenceService(repository=repository).delete_schedule(session, request)
    )

    assert result.success is True
    assert result.deleted_schedule_id == str(schedule.schedule_id)
    assert result.removed_section_ids == [str(section_id)]
    assert repository.deleted_selected_sections is False
    assert repository.deleted_schedule is None
    assert schedule.status == "Archived"
    assert schedule.is_active is False
    assert session.commit_count == 1


def test_service_archives_schedule_without_deleting_sections():
    plan_id = uuid.uuid4()
    schedule = _schedule(plan_id, status="Active")
    section_id = uuid.uuid4()
    repository = _Repository(plan=_plan(plan_id), schedule=schedule)
    repository.replaced_sections = [SimpleNamespace(section_id=section_id)]
    session = _Session()
    request = ActivationRequest(
        user_id=1,
        plan_id=str(plan_id),
        schedule_id=str(schedule.schedule_id),
        confirmed=True,
    )

    result = asyncio.run(
        SchedulePersistenceService(repository=repository).archive_schedule(session, request)
    )

    assert result.status == "Archived"
    assert schedule.is_active is False
    assert result.selected_section_ids == [str(section_id)]
    assert session.commit_count == 1


def test_service_lists_and_loads_schedule_with_schedule_owned_sections():
    plan_id = uuid.uuid4()
    schedule = _schedule(plan_id, status="Draft")
    section_id = uuid.uuid4()
    repository = _Repository(plan=_plan(plan_id), schedule=schedule)
    repository.replaced_sections = [SimpleNamespace(section_id=section_id)]
    service = SchedulePersistenceService(repository=repository)
    session = _Session()

    schedules = asyncio.run(service.list_plan_schedules(session, user_id=1, plan_id=str(plan_id)))
    assert repository.list_schedule_sections_calls == 0
    loaded = asyncio.run(
        service.get_schedule(
            session,
            user_id=1,
            plan_id=str(plan_id),
            schedule_id=str(schedule.schedule_id),
        )
    )

    assert schedules[0].schedule_id == str(schedule.schedule_id)
    assert schedules[0].selected_section_ids == [str(section_id)]
    assert loaded.schedule_id == str(schedule.schedule_id)
    assert loaded.selected_section_ids == [str(section_id)]


def test_service_reconstructs_full_saved_schedule_detail_with_snapshots():
    plan_id = uuid.uuid4()
    schedule = _schedule(plan_id, status="Draft")
    section_id = uuid.uuid4()
    section_row = SimpleNamespace(
        id=uuid.uuid4(),
        schedule_id=schedule.schedule_id,
        section_id=section_id,
        display_order=0,
        course_id_snapshot=uuid.uuid4(),
        section_number_snapshot="001",
        crn_snapshot="12345",
        instruction_method_snapshot="In Person",
        meeting_snapshot=[{"meeting_id": "meeting-1", "section_id": str(section_id)}],
        notes="source_option_id=schedule-option-000001",
        created_at=datetime(2026, 6, 1, 9, 1),
    )
    repository = _Repository(plan=_plan(plan_id), schedule=schedule)
    repository.replaced_sections = [section_row]
    session = _Session()

    detail = asyncio.run(
        SchedulePersistenceService(repository=repository).get_saved_schedule(
            session,
            user_id=1,
            plan_id=str(plan_id),
            schedule_id=str(schedule.schedule_id),
        )
    )

    assert detail.schedule_id == str(schedule.schedule_id)
    assert detail.selected_term_id == str(schedule.selected_term_id)
    assert detail.normalized_score == 80
    assert detail.rank_at_generation == 1
    assert detail.metrics_snapshot == {"total_credits": 3}
    assert detail.tradeoffs_snapshot == ["High seat availability"]
    assert detail.explanation_snapshot["content"] == "Rule-based option."
    assert detail.generation_metadata["source_option_id"] == "option-1"
    assert detail.selected_sections[0].section_id == str(section_id)
    assert detail.selected_sections[0].meeting_snapshot == [
        {"meeting_id": "meeting-1", "section_id": str(section_id)}
    ]
