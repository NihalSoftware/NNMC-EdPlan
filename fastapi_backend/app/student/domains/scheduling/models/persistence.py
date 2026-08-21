from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PlanSection(Base):
    __tablename__ = "plan_sections"
    __table_args__ = (
        UniqueConstraint("plan_id", "section_id", name="plan_sections_plan_section_uk"),
        CheckConstraint(
            "enrollment_status IN ('Planned', 'Enrolled', 'Waitlisted', 'Completed')",
            name="plan_sections_enrollment_status_chk",
        ),
        Index("idx_plan_sections_plan_id", "plan_id"),
        Index("idx_plan_sections_section_id", "section_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ed_plans.plan_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sections.section_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    is_enrolled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    enrollment_status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'Planned'"),
    )
    notes: Mapped[str | None] = mapped_column(Text)

    plan = relationship("EdPlan")
    section = relationship("Section")


class PlanSchedule(Base):
    __tablename__ = "plan_schedules"
    __table_args__ = (
        CheckConstraint("total_credits >= 0", name="plan_schedules_total_credits_chk"),
        CheckConstraint(
            "status IN ('Draft', 'Active', 'Final', 'Archived')",
            name="plan_schedules_status_chk",
        ),
        Index("idx_plan_schedules_plan_id", "plan_id"),
        Index(
            "ux_plan_schedules_one_active_per_plan",
            "plan_id",
            unique=True,
            postgresql_where=text("status = 'Active'"),
        ),
    )

    schedule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ed_plans.plan_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    total_credits: Mapped[Decimal] = mapped_column(
        Numeric(7, 2),
        nullable=False,
        server_default=text("0"),
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'Draft'"),
    )
    notes: Mapped[str | None] = mapped_column(Text)

    plan = relationship("EdPlan")


class SchedulePilotSchedule(Base):
    __tablename__ = "schedule_pilot_schedules"
    __table_args__ = (
        CheckConstraint(
            "status IN ('Draft', 'Active', 'Final', 'Archived', 'Deleted')",
            name="schedule_pilot_schedules_status_chk",
        ),
        CheckConstraint(
            "source IN ('system_generated', 'user_created', 'ai_generated', 'conversation_edit')",
            name="schedule_pilot_schedules_source_chk",
        ),
        CheckConstraint(
            "total_credits >= 0",
            name="schedule_pilot_schedules_total_credits_chk",
        ),
        Index("idx_schedule_pilot_schedules_plan_id", "plan_id"),
        Index("idx_schedule_pilot_schedules_parent_schedule_id", "parent_schedule_id"),
        Index("idx_schedule_pilot_schedules_plan_status", "plan_id", "status"),
        Index("idx_schedule_pilot_schedules_plan_favorite", "plan_id", "is_favorite"),
        Index("idx_schedule_pilot_schedules_selected_term_id", "selected_term_id"),
        Index("idx_schedule_pilot_schedules_created_at", "created_at"),
        Index(
            "ux_schedule_pilot_schedules_one_active_per_plan",
            "plan_id",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )

    schedule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("ed_plans.plan_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    parent_schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey(
            "schedule_pilot_schedules.schedule_id",
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
    )
    schedule_name: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'Draft'"),
    )
    source: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        server_default=text("'system_generated'"),
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    is_favorite: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        server_default=text("false"),
    )
    total_credits: Mapped[Decimal] = mapped_column(
        Numeric(7, 2),
        nullable=False,
        server_default=text("0"),
    )
    score: Mapped[float | None] = mapped_column(Float)
    normalized_score: Mapped[float | None] = mapped_column(Float)
    rank_at_generation: Mapped[int | None] = mapped_column(Integer)
    selected_term_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("academic_terms.term_id", onupdate="CASCADE", ondelete="SET NULL"),
    )
    metrics_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    conflicts_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    warnings_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    tradeoffs_snapshot: Mapped[list[str | dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    explanation_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    generation_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'{}'::jsonb"),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    plan = relationship("EdPlan")
    parent_schedule: Mapped[SchedulePilotSchedule | None] = relationship(
        "SchedulePilotSchedule",
        remote_side=[schedule_id],
    )
    selected_term = relationship("AcademicTerm")
    sections: Mapped[list[SchedulePilotScheduleSection]] = relationship(
        back_populates="schedule",
        cascade="all, delete-orphan",
    )


class SchedulePilotScheduleSection(Base):
    __tablename__ = "schedule_pilot_schedule_sections"
    __table_args__ = (
        UniqueConstraint(
            "schedule_id",
            "section_id",
            name="schedule_pilot_schedule_sections_schedule_section_uk",
        ),
        Index("idx_schedule_pilot_schedule_sections_schedule_id", "schedule_id"),
        Index("idx_schedule_pilot_schedule_sections_section_id", "section_id"),
        Index(
            "idx_schedule_pilot_schedule_sections_display_order",
            "schedule_id",
            "display_order",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    schedule_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey(
            "schedule_pilot_schedules.schedule_id",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sections.section_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default=text("0"),
    )
    course_id_snapshot: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    section_number_snapshot: Mapped[str | None] = mapped_column(String(20))
    crn_snapshot: Mapped[str | None] = mapped_column(String(30))
    instruction_method_snapshot: Mapped[str | None] = mapped_column(String(40))
    meeting_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        server_default=text("'[]'::jsonb"),
    )
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    schedule: Mapped[SchedulePilotSchedule] = relationship(back_populates="sections")
    section = relationship("Section")
