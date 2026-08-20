from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class StudentPreference(Base):
    """ORM mapping for existing student preference records."""

    __tablename__ = "student_preferences"
    __table_args__ = {"schema": "agentic"}

    preference_id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("ed_plans.plan_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    preference_key: Mapped[str] = mapped_column(String(128), nullable=False)
    preference_value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class ConversationMemory(Base):
    """ORM mapping for existing conversation memory summaries."""

    __tablename__ = "conversation_memory"
    __table_args__ = {"schema": "agentic"}

    memory_id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("ed_plans.plan_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_id: Mapped[UUID | None] = mapped_column(
        Uuid,
        ForeignKey("agentic.orchestrator_runs.run_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class OrchestratorRun(Base):
    """ORM mapping for existing orchestrator run traces."""

    __tablename__ = "orchestrator_runs"
    __table_args__ = {"schema": "agentic"}

    run_id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()")
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    plan_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("ed_plans.plan_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    intent: Mapped[str | None] = mapped_column(String(128), nullable=True)
    selected_modules: Mapped[list[str]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class ModuleExecution(Base):
    """ORM mapping for existing per-module execution traces."""

    __tablename__ = "module_executions"
    __table_args__ = {"schema": "agentic"}

    execution_id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()")
    )
    run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("agentic.orchestrator_runs.run_id", ondelete="CASCADE"), index=True
    )
    module_name: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    success: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class WorkflowEvent(Base):
    """ORM mapping for existing workflow event traces."""

    __tablename__ = "workflow_events"
    __table_args__ = {"schema": "agentic"}

    event_id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid4, server_default=text("gen_random_uuid()")
    )
    run_id: Mapped[UUID] = mapped_column(
        Uuid, ForeignKey("agentic.orchestrator_runs.run_id", ondelete="CASCADE"), index=True
    )
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    event_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
