from __future__ import annotations

import uuid
from datetime import date, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.student.domains.discovery.models import Course


class AcademicTerm(Base):
    __tablename__ = "academic_terms"
    __table_args__ = (
        UniqueConstraint("term_name", name="academic_terms_name_uk"),
        CheckConstraint("start_date < end_date", name="academic_terms_date_chk"),
        Index("idx_academic_terms_is_active", "is_active"),
    )

    term_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    term_name: Mapped[str] = mapped_column(String(80), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"))

    offerings: Mapped[list[CourseOffering]] = relationship(back_populates="term")


class CourseOffering(Base):
    __tablename__ = "course_offerings"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "term_id",
            "offering_type",
            name="course_offerings_course_term_type_uk",
        ),
        CheckConstraint(
            "offering_type IN ('Lecture', 'Lab', 'Lecture+Lab', 'Online')",
            name="course_offerings_type_chk",
        ),
        Index("idx_course_offerings_course_id", "course_id"),
        Index("idx_course_offerings_term_id", "term_id"),
    )

    offering_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("courses.course_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    term_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("academic_terms.term_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    offering_type: Mapped[str] = mapped_column(String(30), nullable=False)

    course: Mapped[Course] = relationship()
    term: Mapped[AcademicTerm] = relationship(back_populates="offerings")
    sections: Mapped[list[Section]] = relationship(back_populates="offering")


class Section(Base):
    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("crn", name="sections_crn_uk"),
        UniqueConstraint("offering_id", "section_number", name="sections_offering_section_uk"),
        CheckConstraint("capacity >= 0", name="sections_capacity_chk"),
        CheckConstraint("enrolled >= 0 AND enrolled <= capacity", name="sections_enrolled_chk"),
        CheckConstraint(
            "instruction_method IN ('In Person', 'Online', 'Hybrid')",
            name="sections_instruction_method_chk",
        ),
        CheckConstraint("status IN ('Open', 'Closed', 'Cancelled')", name="sections_status_chk"),
        Index("idx_sections_offering_id", "offering_id"),
        Index("idx_sections_offering_status", "offering_id", "status"),
        Index("idx_sections_status", "status"),
    )

    section_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    offering_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("course_offerings.offering_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    section_number: Mapped[str] = mapped_column(String(20), nullable=False)
    crn: Mapped[str] = mapped_column(String(30), nullable=False)
    campus: Mapped[str | None] = mapped_column(String(120))
    instructor: Mapped[str | None] = mapped_column(String(150))
    instruction_method: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        server_default=text("'In Person'"),
    )
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    enrolled: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    status: Mapped[str] = mapped_column(String(20), nullable=False, server_default=text("'Open'"))

    offering: Mapped[CourseOffering] = relationship(back_populates="sections")
    meetings: Mapped[list[SectionMeeting]] = relationship(back_populates="section")


class SectionMeeting(Base):
    __tablename__ = "section_meetings"
    __table_args__ = (
        UniqueConstraint(
            "section_id",
            "weekday",
            "start_time",
            "end_time",
            "meeting_type",
            name="section_meetings_unique_time_uk",
            postgresql_nulls_not_distinct=True,
        ),
        CheckConstraint(
            "weekday IS NULL AND start_time IS NULL AND end_time IS NULL OR "
            "weekday IS NOT NULL AND start_time IS NOT NULL AND end_time IS NOT NULL "
            "AND start_time < end_time",
            name="section_meetings_time_pair_chk",
        ),
        CheckConstraint(
            "meeting_type IN ('Class', 'Lab', 'Exam', 'Online Async')",
            name="section_meetings_type_chk",
        ),
        CheckConstraint(
            "weekday IS NULL OR weekday >= 1 AND weekday <= 7",
            name="section_meetings_weekday_chk",
        ),
        Index("idx_section_meetings_conflict_lookup", "weekday", "start_time", "end_time"),
        Index("idx_section_meetings_section_id", "section_id"),
    )

    meeting_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    section_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("sections.section_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    weekday: Mapped[int | None] = mapped_column(SmallInteger)
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)
    building: Mapped[str | None] = mapped_column(String(80))
    room: Mapped[str | None] = mapped_column(String(40))
    meeting_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        server_default=text("'Class'"),
    )

    section: Mapped[Section] = relationship(back_populates="meetings")
