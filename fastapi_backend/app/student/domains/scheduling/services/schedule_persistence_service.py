from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.student.domains.scheduling.models import SchedulePilotSchedule
from app.student.domains.scheduling.repositories.schedule_persistence_repository import (
    SchedulePersistenceRepository,
    schedule_persistence_repository,
)
from app.student.domains.scheduling.schemas.schedule_persistence import (
    ActivationRequest,
    ActivationResult,
    DeleteScheduleRequest,
    DeleteScheduleResult,
    SavedScheduleDetail,
    SavedScheduleSectionDetail,
    SaveScheduleRequest,
    SaveScheduleResult,
    ScheduleSummary,
)


class SchedulePersistenceService:
    def __init__(
        self,
        repository: SchedulePersistenceRepository | None = None,
    ) -> None:
        self.repository = repository or schedule_persistence_repository

    async def save_schedule(
        self,
        db: AsyncSession,
        request: SaveScheduleRequest,
    ) -> SaveScheduleResult:
        try:
            await self._validate_owned_plan(
                db,
                user_id=request.user_id,
                plan_id=request.plan_id,
            )
            section_ids = [
                section.section_id for section in request.selected_option.selected_sections
            ]
            section_snapshots = await self._load_validated_section_snapshots(
                db,
                selected_option=request.selected_option,
                section_ids=section_ids,
            )
            total_credits = (
                request.selected_option.metrics.total_credits
                if request.selected_option.metrics is not None
                else 0
            )
            schedule = await self.repository.create_schedule(
                db,
                plan_id=request.plan_id,
                total_credits=total_credits,
                status="Final" if request.confirmed else "Draft",
                schedule_name=request.schedule_name,
                source="user_created" if request.confirmed else "system_generated",
                score=request.selected_option.score,
                normalized_score=request.selected_option.normalized_score,
                rank_at_generation=request.selected_option.rank,
                selected_term_id=_selected_term_id(request.selected_option),
                metrics_snapshot=(
                    request.selected_option.metrics.model_dump(mode="json")
                    if request.selected_option.metrics is not None
                    else {}
                ),
                conflicts_snapshot=[
                    conflict.model_dump(mode="json")
                    for conflict in request.selected_option.conflicts
                ],
                warnings_snapshot=[
                    warning.model_dump(mode="json") for warning in request.selected_option.warnings
                ],
                tradeoffs_snapshot=list(request.selected_option.tradeoffs),
                explanation_snapshot={
                    "content": request.selected_option.explanation,
                    "source": "rule_based",
                },
                generation_metadata=_schedule_metadata(
                    request.notes,
                    {
                        "source_option_id": request.selected_option.option_id,
                        "rank": request.selected_option.rank,
                        "metadata": request.selected_option.metadata,
                    },
                ),
            )
            selected_sections = await self.repository.replace_schedule_sections(
                db,
                schedule_id=schedule.schedule_id,
                sections=section_snapshots,
                notes=f"source_option_id={request.selected_option.option_id}",
            )
            await db.commit()
            return SaveScheduleResult(
                success=True,
                schedule=_schedule_summary(
                    schedule,
                    selected_section_ids=[str(item.section_id) for item in selected_sections],
                ),
            )
        except Exception:
            await db.rollback()
            raise

    async def activate_schedule(
        self,
        db: AsyncSession,
        request: ActivationRequest,
    ) -> ActivationResult:
        try:
            await self._validate_owned_plan(
                db,
                user_id=request.user_id,
                plan_id=request.plan_id,
            )
            if not request.confirmed:
                raise ValueError("Schedule activation requires confirmation.")
            schedule = await self._validate_schedule(
                db,
                schedule_id=request.schedule_id,
                plan_id=request.plan_id,
            )
            deactivated = await self.repository.deactivate_plan_schedules(
                db,
                plan_id=request.plan_id,
                except_schedule_id=request.schedule_id,
            )
            await self.repository.activate_schedule(schedule)
            selected_sections = await self.repository.list_schedule_sections(
                db,
                schedule_id=request.schedule_id,
            )
            await db.commit()
            return ActivationResult(
                success=True,
                activated_schedule=_schedule_summary(
                    schedule,
                    selected_section_ids=[str(item.section_id) for item in selected_sections],
                ),
                deactivated_schedule_ids=[str(item.schedule_id) for item in deactivated],
            )
        except Exception:
            await db.rollback()
            raise

    async def delete_schedule(
        self,
        db: AsyncSession,
        request: DeleteScheduleRequest,
    ) -> DeleteScheduleResult:
        try:
            await self._validate_owned_plan(
                db,
                user_id=request.user_id,
                plan_id=request.plan_id,
            )
            if not request.confirmed:
                raise ValueError("Schedule deletion requires confirmation.")
            schedule = await self._validate_schedule(
                db,
                schedule_id=request.schedule_id,
                plan_id=request.plan_id,
            )
            selected_sections = await self.repository.list_schedule_sections(
                db,
                schedule_id=request.schedule_id,
            )
            removed_section_ids = [str(item.section_id) for item in selected_sections]
            await self.repository.archive_schedule(schedule)
            await db.commit()
            return DeleteScheduleResult(
                success=True,
                deleted_schedule_id=request.schedule_id,
                removed_section_ids=removed_section_ids,
            )
        except Exception:
            await db.rollback()
            raise

    async def archive_schedule(
        self,
        db: AsyncSession,
        request: ActivationRequest,
    ) -> ScheduleSummary:
        try:
            await self._validate_owned_plan(
                db,
                user_id=request.user_id,
                plan_id=request.plan_id,
            )
            schedule = await self._validate_schedule(
                db,
                schedule_id=request.schedule_id,
                plan_id=request.plan_id,
            )
            await self.repository.archive_schedule(schedule)
            selected_sections = await self.repository.list_schedule_sections(
                db,
                schedule_id=request.schedule_id,
            )
            await db.commit()
            return _schedule_summary(
                schedule,
                selected_section_ids=[str(item.section_id) for item in selected_sections],
            )
        except Exception:
            await db.rollback()
            raise

    async def list_plan_schedules(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        plan_id: str,
    ) -> list[ScheduleSummary]:
        await self._validate_owned_plan(db, user_id=user_id, plan_id=plan_id)
        schedules, sections_by_schedule = await self.repository.list_schedules_with_sections(
            db,
            plan_id=plan_id,
        )
        return [
            _schedule_summary(
                schedule,
                selected_section_ids=[
                    str(item.section_id)
                    for item in sections_by_schedule.get(schedule.schedule_id, [])
                ],
            )
            for schedule in schedules
        ]

    async def get_schedule(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        plan_id: str,
        schedule_id: str,
    ) -> ScheduleSummary:
        await self._validate_owned_plan(db, user_id=user_id, plan_id=plan_id)
        schedule = await self._validate_schedule(
            db,
            schedule_id=schedule_id,
            plan_id=plan_id,
        )
        selected_sections = await self.repository.list_schedule_sections(
            db,
            schedule_id=schedule_id,
        )
        return _schedule_summary(
            schedule,
            selected_section_ids=[str(item.section_id) for item in selected_sections],
        )

    async def get_saved_schedule(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        plan_id: str,
        schedule_id: str,
    ) -> SavedScheduleDetail:
        await self._validate_owned_plan(db, user_id=user_id, plan_id=plan_id)
        schedule, selected_sections = await self.repository.get_schedule_with_sections(
            db,
            schedule_id=schedule_id,
        )
        if schedule is None:
            raise ValueError("Schedule not found.")
        if str(schedule.plan_id) != str(plan_id):
            raise PermissionError("Schedule does not belong to the requested plan.")
        return _schedule_detail(schedule, selected_sections=selected_sections)

    async def _validate_owned_plan(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        plan_id: str,
    ):
        plan = await self.repository.get_plan(db, plan_id=plan_id)
        if plan is None:
            raise ValueError("Plan not found.")
        if plan.user_id != user_id:
            raise PermissionError("Plan does not belong to the requested user.")
        return plan

    async def _load_validated_section_snapshots(
        self,
        db: AsyncSession,
        *,
        selected_option,
        section_ids: list[str],
    ) -> list[dict]:
        if not section_ids:
            raise ValueError("A schedule option must contain at least one selected section.")
        section_snapshots = await self.repository.get_section_snapshots_by_ids(
            db,
            section_ids=section_ids,
        )
        existing_ids = {snapshot["section_id"] for snapshot in section_snapshots}
        missing_ids = [
            section_id for section_id in section_ids if str(section_id) not in existing_ids
        ]
        if missing_ids:
            raise ValueError(f"Selected sections do not exist: {', '.join(missing_ids)}")
        meetings_by_section: dict[str, list[dict]] = {}
        for meeting in selected_option.selected_meetings:
            meetings_by_section.setdefault(str(meeting.section_id), []).append(
                meeting.model_dump(mode="json")
            )
        snapshot_by_section = {snapshot["section_id"]: snapshot for snapshot in section_snapshots}
        ordered_snapshots = []
        for section_id in section_ids:
            snapshot = dict(snapshot_by_section[str(section_id)])
            snapshot["meeting_snapshot"] = meetings_by_section.get(str(section_id), [])
            ordered_snapshots.append(snapshot)
        return ordered_snapshots

    async def _validate_schedule(
        self,
        db: AsyncSession,
        *,
        schedule_id: str,
        plan_id: str,
    ) -> SchedulePilotSchedule:
        schedule = await self.repository.get_schedule(db, schedule_id=schedule_id)
        if schedule is None:
            raise ValueError("Schedule not found.")
        if str(schedule.plan_id) != str(plan_id):
            raise PermissionError("Schedule does not belong to the requested plan.")
        return schedule


def _schedule_notes(schedule_name: str | None, notes: str | None) -> str | None:
    if schedule_name and notes:
        return f"{schedule_name}\n\n{notes}"
    return schedule_name or notes


def _schedule_summary(
    schedule: SchedulePilotSchedule,
    *,
    selected_section_ids: list[str],
) -> ScheduleSummary:
    return ScheduleSummary(
        schedule_id=str(schedule.schedule_id),
        plan_id=str(schedule.plan_id),
        schedule_name=schedule.schedule_name,
        status=schedule.status,
        is_active=schedule.is_active,
        is_favorite=schedule.is_favorite,
        total_credits=float(schedule.total_credits),
        notes=(schedule.generation_metadata or {}).get("notes"),
        generated_at=schedule.created_at,
        selected_section_ids=selected_section_ids,
    )


def _schedule_detail(
    schedule: SchedulePilotSchedule,
    *,
    selected_sections,
) -> SavedScheduleDetail:
    section_details = [
        SavedScheduleSectionDetail(
            id=str(section.id),
            schedule_id=str(section.schedule_id),
            section_id=str(section.section_id),
            display_order=section.display_order,
            course_id_snapshot=(
                str(section.course_id_snapshot) if section.course_id_snapshot else None
            ),
            section_number_snapshot=section.section_number_snapshot,
            crn_snapshot=section.crn_snapshot,
            instruction_method_snapshot=section.instruction_method_snapshot,
            meeting_snapshot=section.meeting_snapshot or [],
            notes=section.notes,
            created_at=section.created_at,
        )
        for section in selected_sections
    ]
    return SavedScheduleDetail(
        schedule_id=str(schedule.schedule_id),
        plan_id=str(schedule.plan_id),
        parent_schedule_id=(
            str(schedule.parent_schedule_id) if schedule.parent_schedule_id else None
        ),
        selected_term_id=str(schedule.selected_term_id) if schedule.selected_term_id else None,
        schedule_name=schedule.schedule_name,
        status=schedule.status,
        source=schedule.source,
        is_active=schedule.is_active,
        is_favorite=schedule.is_favorite,
        total_credits=float(schedule.total_credits),
        score=schedule.score,
        normalized_score=schedule.normalized_score,
        rank_at_generation=schedule.rank_at_generation,
        metrics_snapshot=schedule.metrics_snapshot or {},
        conflicts_snapshot=schedule.conflicts_snapshot or [],
        warnings_snapshot=schedule.warnings_snapshot or [],
        tradeoffs_snapshot=schedule.tradeoffs_snapshot or [],
        explanation_snapshot=schedule.explanation_snapshot or {},
        generation_metadata=schedule.generation_metadata or {},
        selected_sections=section_details,
        selected_section_ids=[section.section_id for section in section_details],
        created_at=schedule.created_at,
        updated_at=schedule.updated_at,
        archived_at=schedule.archived_at,
        deleted_at=schedule.deleted_at,
    )


def _schedule_metadata(notes: str | None, metadata: dict | None = None) -> dict:
    payload = dict(metadata or {})
    if notes:
        payload["notes"] = notes
    return payload


def _selected_term_id(selected_option) -> str | None:
    term_ids = {
        str(section.term_id)
        for section in selected_option.selected_sections
        if getattr(section, "term_id", None)
    }
    return next(iter(term_ids)) if len(term_ids) == 1 else None


schedule_persistence_service = SchedulePersistenceService()
