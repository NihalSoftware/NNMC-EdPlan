from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.constants.institution import NORTHERN_NEW_MEXICO_COLLEGE_NAME
from app.student.domains.discovery.models import University
from app.student.domains.planning.models import EdPlan
from app.student.domains.scheduling.models import (
    CourseOffering,
    PlanSchedule,
    PlanSection,
    SchedulePilotSchedule,
    SchedulePilotScheduleSection,
    Section,
)


class SchedulePersistenceRepository:
    async def get_plan(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
    ) -> EdPlan | None:
        parsed_plan_id = _parse_uuid(plan_id)
        if parsed_plan_id is None:
            return None
        result = await db.execute(
            select(EdPlan).where(
                EdPlan.plan_id == parsed_plan_id,
                EdPlan.university.has(
                    University.university_name.ilike(NORTHERN_NEW_MEXICO_COLLEGE_NAME)
                ),
            )
        )
        return result.scalar_one_or_none()

    async def get_sections_by_ids(
        self,
        db: AsyncSession,
        *,
        section_ids: Sequence[str | uuid.UUID],
    ) -> list[Section]:
        parsed_section_ids = _parse_uuid_list(section_ids)
        if not parsed_section_ids:
            return []
        result = await db.execute(select(Section).where(Section.section_id.in_(parsed_section_ids)))
        return list(result.scalars().all())

    async def get_section_snapshots_by_ids(
        self,
        db: AsyncSession,
        *,
        section_ids: Sequence[str | uuid.UUID],
    ) -> list[dict]:
        parsed_section_ids = _parse_uuid_list(section_ids)
        if not parsed_section_ids:
            return []
        result = await db.execute(
            select(Section, CourseOffering.course_id)
            .join(CourseOffering, Section.offering_id == CourseOffering.offering_id)
            .where(Section.section_id.in_(parsed_section_ids))
        )
        snapshots = []
        for section, course_id in result.all():
            snapshots.append(
                {
                    "section_id": str(section.section_id),
                    "course_id_snapshot": str(course_id) if course_id else None,
                    "section_number_snapshot": section.section_number,
                    "crn_snapshot": section.crn,
                    "instruction_method_snapshot": section.instruction_method,
                }
            )
        return snapshots

    async def create_schedule(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
        total_credits: int,
        status: str = "Draft",
        schedule_name: str | None = None,
        source: str = "system_generated",
        score: float | None = None,
        normalized_score: float | None = None,
        rank_at_generation: int | None = None,
        selected_term_id: str | uuid.UUID | None = None,
        metrics_snapshot: dict | None = None,
        conflicts_snapshot: list | None = None,
        warnings_snapshot: list | None = None,
        tradeoffs_snapshot: list | None = None,
        explanation_snapshot: dict | None = None,
        generation_metadata: dict | None = None,
        notes: str | None = None,
    ) -> SchedulePilotSchedule:
        parsed_plan_id = _require_uuid(plan_id, "plan_id")
        schedule = SchedulePilotSchedule(
            plan_id=parsed_plan_id,
            schedule_name=schedule_name,
            total_credits=total_credits,
            status=status,
            source=source,
            is_active=False,
            is_favorite=False,
            score=score,
            normalized_score=normalized_score,
            rank_at_generation=rank_at_generation,
            selected_term_id=(
                _require_uuid(selected_term_id, "selected_term_id")
                if selected_term_id is not None
                else None
            ),
            metrics_snapshot=metrics_snapshot or {},
            conflicts_snapshot=conflicts_snapshot or [],
            warnings_snapshot=warnings_snapshot or [],
            tradeoffs_snapshot=tradeoffs_snapshot or [],
            explanation_snapshot=explanation_snapshot or {},
            generation_metadata=_schedule_metadata(notes, generation_metadata),
        )
        db.add(schedule)
        await db.flush()
        return schedule

    async def update_schedule(
        self,
        schedule: SchedulePilotSchedule,
        *,
        total_credits: int | None = None,
        status: str | None = None,
        schedule_name: str | None = None,
        update_schedule_name: bool = False,
    ) -> SchedulePilotSchedule:
        if total_credits is not None:
            schedule.total_credits = total_credits
        if status is not None:
            schedule.status = status
        if update_schedule_name:
            schedule.schedule_name = schedule_name
        return schedule

    async def delete_schedule(self, db: AsyncSession, schedule: SchedulePilotSchedule) -> None:
        await db.delete(schedule)
        await db.flush()

    async def get_schedule(
        self,
        db: AsyncSession,
        *,
        schedule_id: str | uuid.UUID,
    ) -> SchedulePilotSchedule | None:
        parsed_schedule_id = _parse_uuid(schedule_id)
        if parsed_schedule_id is None:
            return None
        result = await db.execute(
            select(SchedulePilotSchedule).where(
                SchedulePilotSchedule.schedule_id == parsed_schedule_id
            )
        )
        return result.scalar_one_or_none()

    async def get_schedule_with_sections(
        self,
        db: AsyncSession,
        *,
        schedule_id: str | uuid.UUID,
    ) -> tuple[SchedulePilotSchedule | None, list[SchedulePilotScheduleSection]]:
        parsed_schedule_id = _parse_uuid(schedule_id)
        if parsed_schedule_id is None:
            return None, []
        result = await db.execute(
            select(SchedulePilotSchedule, SchedulePilotScheduleSection)
            .outerjoin(
                SchedulePilotScheduleSection,
                SchedulePilotSchedule.schedule_id == SchedulePilotScheduleSection.schedule_id,
            )
            .where(SchedulePilotSchedule.schedule_id == parsed_schedule_id)
            .order_by(
                SchedulePilotScheduleSection.display_order,
                SchedulePilotScheduleSection.id,
            )
        )
        rows = result.all()
        if not rows:
            return None, []
        schedule = rows[0][0]
        sections = [row[1] for row in rows if row[1] is not None]
        return schedule, sections

    async def list_schedules(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
    ) -> list[SchedulePilotSchedule]:
        parsed_plan_id = _parse_uuid(plan_id)
        if parsed_plan_id is None:
            return []
        result = await db.execute(
            select(SchedulePilotSchedule)
            .where(SchedulePilotSchedule.plan_id == parsed_plan_id)
            .where(SchedulePilotSchedule.deleted_at.is_(None))
            .order_by(
                SchedulePilotSchedule.created_at.desc(),
                SchedulePilotSchedule.schedule_id,
            )
        )
        return list(result.scalars().all())

    async def list_schedules_with_sections(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
    ) -> tuple[
        list[SchedulePilotSchedule],
        dict[uuid.UUID, list[SchedulePilotScheduleSection]],
    ]:
        schedules = await self.list_schedules(db, plan_id=plan_id)
        schedule_sections = await self.list_schedule_sections_for_schedules(
            db,
            schedule_ids=[schedule.schedule_id for schedule in schedules],
        )
        sections_by_schedule: dict[uuid.UUID, list[SchedulePilotScheduleSection]] = {
            schedule.schedule_id: [] for schedule in schedules
        }
        for section in schedule_sections:
            sections_by_schedule.setdefault(section.schedule_id, []).append(section)
        return schedules, sections_by_schedule

    async def list_plan_schedules(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
    ) -> list[SchedulePilotSchedule]:
        return await self.list_schedules(db, plan_id=plan_id)

    async def get_active_schedule(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
    ) -> SchedulePilotSchedule | None:
        parsed_plan_id = _parse_uuid(plan_id)
        if parsed_plan_id is None:
            return None
        result = await db.execute(
            select(SchedulePilotSchedule)
            .where(SchedulePilotSchedule.plan_id == parsed_plan_id)
            .where(SchedulePilotSchedule.is_active.is_(True))
            .where(SchedulePilotSchedule.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def deactivate_plan_schedules(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
        except_schedule_id: str | uuid.UUID | None = None,
    ) -> list[SchedulePilotSchedule]:
        parsed_plan_id = _require_uuid(plan_id, "plan_id")
        active_schedule = await self.get_active_schedule(db, plan_id=parsed_plan_id)
        deactivated: list[SchedulePilotSchedule] = []
        if active_schedule is not None and (
            except_schedule_id is None
            or active_schedule.schedule_id != _parse_uuid(except_schedule_id)
        ):
            active_schedule.is_active = False
            active_schedule.status = "Archived"
            deactivated.append(active_schedule)
        return deactivated

    async def activate_schedule(self, schedule: SchedulePilotSchedule) -> SchedulePilotSchedule:
        schedule.is_active = True
        schedule.status = "Active"
        return schedule

    async def deactivate_schedule(
        self,
        schedule: SchedulePilotSchedule,
        *,
        status: str = "Archived",
    ) -> SchedulePilotSchedule:
        schedule.is_active = False
        schedule.status = status
        return schedule

    async def archive_schedule(self, schedule: SchedulePilotSchedule) -> SchedulePilotSchedule:
        schedule.is_active = False
        schedule.status = "Archived"
        return schedule

    async def save_schedule_sections(
        self,
        db: AsyncSession,
        *,
        schedule_id: str | uuid.UUID,
        sections: list[dict],
        notes: str | None = None,
    ) -> list[SchedulePilotScheduleSection]:
        parsed_schedule_id = _require_uuid(schedule_id, "schedule_id")
        schedule_sections = [
            SchedulePilotScheduleSection(
                schedule_id=parsed_schedule_id,
                section_id=_require_uuid(section["section_id"], "section_id"),
                display_order=index,
                course_id_snapshot=(
                    _require_uuid(section["course_id_snapshot"], "course_id_snapshot")
                    if section.get("course_id_snapshot") is not None
                    else None
                ),
                section_number_snapshot=section.get("section_number_snapshot"),
                crn_snapshot=section.get("crn_snapshot"),
                instruction_method_snapshot=section.get("instruction_method_snapshot"),
                meeting_snapshot=section.get("meeting_snapshot") or [],
                notes=notes,
            )
            for index, section in enumerate(sections)
        ]
        for schedule_section in schedule_sections:
            db.add(schedule_section)
        await db.flush()
        return schedule_sections

    async def replace_schedule_sections(
        self,
        db: AsyncSession,
        *,
        schedule_id: str | uuid.UUID,
        sections: list[dict],
        notes: str | None = None,
    ) -> list[SchedulePilotScheduleSection]:
        await self.delete_schedule_sections(db, schedule_id=schedule_id)
        return await self.save_schedule_sections(
            db,
            schedule_id=schedule_id,
            sections=sections,
            notes=notes,
        )

    async def delete_schedule_sections(
        self,
        db: AsyncSession,
        *,
        schedule_id: str | uuid.UUID,
    ) -> None:
        parsed_schedule_id = _require_uuid(schedule_id, "schedule_id")
        await db.execute(
            delete(SchedulePilotScheduleSection).where(
                SchedulePilotScheduleSection.schedule_id == parsed_schedule_id
            )
        )
        await db.flush()

    async def list_schedule_sections(
        self,
        db: AsyncSession,
        *,
        schedule_id: str | uuid.UUID,
    ) -> list[SchedulePilotScheduleSection]:
        parsed_schedule_id = _parse_uuid(schedule_id)
        if parsed_schedule_id is None:
            return []
        result = await db.execute(
            select(SchedulePilotScheduleSection)
            .where(SchedulePilotScheduleSection.schedule_id == parsed_schedule_id)
            .order_by(
                SchedulePilotScheduleSection.display_order,
                SchedulePilotScheduleSection.id,
            )
        )
        return list(result.scalars().all())

    async def list_schedule_sections_for_schedules(
        self,
        db: AsyncSession,
        *,
        schedule_ids: list[str | uuid.UUID],
    ) -> list[SchedulePilotScheduleSection]:
        parsed_schedule_ids = _parse_uuid_list(schedule_ids)
        if not parsed_schedule_ids:
            return []
        result = await db.execute(
            select(SchedulePilotScheduleSection)
            .where(SchedulePilotScheduleSection.schedule_id.in_(parsed_schedule_ids))
            .order_by(
                SchedulePilotScheduleSection.schedule_id,
                SchedulePilotScheduleSection.display_order,
                SchedulePilotScheduleSection.id,
            )
        )
        return list(result.scalars().all())

    async def save_selected_sections(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
        section_ids: list[str | uuid.UUID],
        notes: str | None = None,
    ) -> list[PlanSection]:
        parsed_plan_id = _require_uuid(plan_id, "plan_id")
        plan_sections = [
            PlanSection(
                plan_id=parsed_plan_id,
                section_id=_require_uuid(section_id, "section_id"),
                is_enrolled=False,
                enrollment_status="Planned",
                notes=notes,
            )
            for section_id in section_ids
        ]
        for plan_section in plan_sections:
            db.add(plan_section)
        await db.flush()
        return plan_sections

    async def replace_selected_sections(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
        section_ids: list[str | uuid.UUID],
        notes: str | None = None,
    ) -> list[PlanSection]:
        await self.delete_selected_sections(db, plan_id=plan_id)
        return await self.save_selected_sections(
            db,
            plan_id=plan_id,
            section_ids=section_ids,
            notes=notes,
        )

    async def delete_selected_sections(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
    ) -> None:
        parsed_plan_id = _require_uuid(plan_id, "plan_id")
        await db.execute(delete(PlanSection).where(PlanSection.plan_id == parsed_plan_id))
        await db.flush()

    async def list_selected_sections(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
    ) -> list[PlanSection]:
        parsed_plan_id = _parse_uuid(plan_id)
        if parsed_plan_id is None:
            return []
        result = await db.execute(
            select(PlanSection)
            .where(PlanSection.plan_id == parsed_plan_id)
            .order_by(PlanSection.id)
        )
        return list(result.scalars().all())

    async def archive_schedule_by_id(
        self,
        db: AsyncSession,
        *,
        schedule_id: str | uuid.UUID,
    ) -> None:
        parsed_schedule_id = _require_uuid(schedule_id, "schedule_id")
        await db.execute(
            update(SchedulePilotSchedule)
            .where(SchedulePilotSchedule.schedule_id == parsed_schedule_id)
            .values(status="Archived", is_active=False)
        )
        await db.flush()

    async def create_legacy_schedule(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
        total_credits: int,
        status: str = "Draft",
        notes: str | None = None,
    ) -> PlanSchedule:
        parsed_plan_id = _require_uuid(plan_id, "plan_id")
        schedule = PlanSchedule(
            plan_id=parsed_plan_id,
            total_credits=total_credits,
            status=status,
            notes=notes,
        )
        db.add(schedule)
        await db.flush()
        return schedule

    async def list_legacy_plan_schedules(
        self,
        db: AsyncSession,
        *,
        plan_id: str | uuid.UUID,
    ) -> list[PlanSchedule]:
        parsed_plan_id = _parse_uuid(plan_id)
        if parsed_plan_id is None:
            return []
        result = await db.execute(
            select(PlanSchedule)
            .where(PlanSchedule.plan_id == parsed_plan_id)
            .order_by(PlanSchedule.generated_at.desc(), PlanSchedule.schedule_id)
        )
        return list(result.scalars().all())


def _parse_uuid(value: str | uuid.UUID) -> uuid.UUID | None:
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (TypeError, ValueError):
        return None


def _require_uuid(value: str | uuid.UUID, field_name: str) -> uuid.UUID:
    parsed = _parse_uuid(value)
    if parsed is None:
        raise ValueError(f"Invalid {field_name}.")
    return parsed


def _parse_uuid_list(values: Sequence[str | uuid.UUID]) -> list[uuid.UUID]:
    parsed_values = [_parse_uuid(value) for value in values]
    return [value for value in parsed_values if value is not None]


def _schedule_metadata(notes: str | None, metadata: dict | None) -> dict:
    payload = dict(metadata or {})
    if notes:
        payload["notes"] = notes
    return payload


schedule_persistence_repository = SchedulePersistenceRepository()
