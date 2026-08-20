from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    and_,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.student.domains.discovery.models import Course, Program, University
from app.student.domains.scheduling.models import AcademicTerm


class EdPlan(Base):
    __tablename__ = "ed_plans"
    __table_args__ = (
        UniqueConstraint("user_id", "plan_name", name="ed_plans_user_name_uk"),
        ForeignKeyConstraint(
            ["program_id", "university_id"],
            ["programs.program_id", "programs.university_id"],
            name="ed_plans_program_university_fk",
            onupdate="CASCADE",
            ondelete="RESTRICT",
        ),
        Index("idx_ed_plans_legacy_education_plan_id", "legacy_education_plan_id", unique=True),
        Index("idx_ed_plans_program_id", "program_id"),
        Index("idx_ed_plans_university_id", "university_id"),
        Index("idx_ed_plans_user_id", "user_id"),
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("universities.university_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    program_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    plan_name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))
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
    legacy_education_plan_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            "education_plans.id",
            name="ed_plans_legacy_education_plan_fk",
            onupdate="CASCADE",
            ondelete="SET NULL",
        ),
    )

    university: Mapped[University] = relationship(foreign_keys=[university_id])
    program: Mapped[Program] = relationship(
        primaryjoin=lambda: and_(
            EdPlan.program_id == Program.program_id,
            EdPlan.university_id == Program.university_id,
        ),
        foreign_keys=lambda: [EdPlan.program_id, EdPlan.university_id],
        viewonly=True,
    )
    courses: Mapped[list[PlanCourse]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
    )


class PlanCourse(Base):
    __tablename__ = "plan_courses"
    __table_args__ = (
        UniqueConstraint("plan_id", "course_id", name="plan_courses_plan_course_uk"),
        CheckConstraint(
            "status IN ('Planned', 'In Progress', 'Completed')",
            name="plan_courses_status_chk",
        ),
        Index("idx_plan_courses_course_id", "course_id"),
        Index("idx_plan_courses_plan_id", "plan_id"),
        Index("idx_plan_courses_planned_term_id", "planned_term_id"),
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
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("courses.course_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    planned_term_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("academic_terms.term_id", onupdate="CASCADE", ondelete="SET NULL"),
    )
    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'Planned'"),
    )
    notes: Mapped[str | None] = mapped_column(Text)

    plan: Mapped[EdPlan] = relationship(back_populates="courses")
    course: Mapped[Course] = relationship()
    planned_term: Mapped[AcademicTerm | None] = relationship()
