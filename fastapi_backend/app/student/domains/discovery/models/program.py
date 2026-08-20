from __future__ import annotations

import uuid

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class University(Base):
    __tablename__ = "universities"
    __table_args__ = (
        UniqueConstraint(
            "university_name",
            "city",
            "state",
            name="universities_name_city_state_uk",
        ),
    )

    university_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    university_name: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    state: Mapped[str] = mapped_column(String(120), nullable=False)
    website: Mapped[str | None] = mapped_column(String(255))
    college_profile: Mapped[dict | None] = mapped_column(JSONB)

    programs: Mapped[list[Program]] = relationship(back_populates="university")


class Program(Base):
    __tablename__ = "programs"
    __table_args__ = (
        UniqueConstraint("program_id", "university_id", name="programs_program_university_uk"),
        UniqueConstraint(
            "university_id",
            "program_name",
            "degree",
            name="programs_university_name_degree_uk",
        ),
        CheckConstraint("total_credit_hours > 0", name="programs_total_credit_hours_chk"),
        Index("idx_programs_university_id", "university_id"),
    )

    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    university_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("universities.university_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    program_name: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str] = mapped_column(String(120), nullable=False)
    total_credit_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)

    university: Mapped[University] = relationship(back_populates="programs")
    courses: Mapped[list[Course]] = relationship(back_populates="program")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (
        UniqueConstraint("program_id", "course_code", name="courses_program_code_uk"),
        CheckConstraint("credits > 0", name="courses_credits_chk"),
        CheckConstraint("lecture_hours >= 0 AND lab_hours >= 0", name="courses_hours_chk"),
        CheckConstraint(
            "recommended_year IS NULL OR recommended_year >= 1 AND recommended_year <= 8",
            name="courses_recommended_year_chk",
        ),
        CheckConstraint(
            "recommended_semester IS NULL OR recommended_semester IN "
            "('Fall', 'Spring', 'Summer', 'Winter')",
            name="courses_recommended_semester_chk",
        ),
        Index("idx_courses_course_code", "course_code"),
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    program_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("programs.program_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )
    course_code: Mapped[str] = mapped_column(String(40), nullable=False)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    lecture_hours: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    lab_hours: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    recommended_year: Mapped[int | None] = mapped_column(Integer)
    recommended_semester: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB)
    source_sequence: Mapped[int | None] = mapped_column(Integer)

    @property
    def is_elective(self) -> bool:
        metadata = self.metadata_json or {}
        explicit_value = metadata.get("is_elective")
        if isinstance(explicit_value, bool):
            return explicit_value
        if explicit_value is not None:
            normalized_value = str(explicit_value).strip().lower()
            if normalized_value in {"true", "1", "yes"}:
                return True
            if normalized_value in {"false", "0", "no"}:
                return False

        code = (self.course_code or "").strip().upper()
        name = (self.course_name or "").strip().lower()
        return code.startswith("ELEC") or "elective" in name

    @property
    def default_plan_eligible(self) -> bool:
        return (
            not self.is_elective
            and self.recommended_year is not None
            and bool(self.recommended_semester)
        )

    program: Mapped[Program] = relationship(back_populates="courses")
    prerequisite_links: Mapped[list[CoursePrerequisite]] = relationship(
        back_populates="course",
        foreign_keys="CoursePrerequisite.course_id",
        cascade="all, delete-orphan",
    )
    required_by_links: Mapped[list[CoursePrerequisite]] = relationship(
        back_populates="prerequisite_course",
        foreign_keys="CoursePrerequisite.prerequisite_course_id",
    )
    corequisite_links: Mapped[list[CourseCorequisite]] = relationship(
        back_populates="course",
        foreign_keys="CourseCorequisite.course_id",
        cascade="all, delete-orphan",
    )
    corequired_by_links: Mapped[list[CourseCorequisite]] = relationship(
        back_populates="corequisite_course",
        foreign_keys="CourseCorequisite.corequisite_course_id",
    )


class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "prerequisite_course_id",
            name="course_prerequisites_pair_uk",
        ),
        CheckConstraint(
            "course_id <> prerequisite_course_id",
            name="course_prerequisites_not_self_chk",
        ),
        Index("idx_course_prerequisites_course_id", "course_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("courses.course_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    prerequisite_course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("courses.course_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )

    course: Mapped[Course] = relationship(
        back_populates="prerequisite_links",
        foreign_keys=[course_id],
    )
    prerequisite_course: Mapped[Course] = relationship(
        back_populates="required_by_links",
        foreign_keys=[prerequisite_course_id],
    )


class CourseCorequisite(Base):
    __tablename__ = "course_corequisites"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "corequisite_course_id",
            name="course_corequisites_pair_uk",
        ),
        CheckConstraint(
            "course_id <> corequisite_course_id",
            name="course_corequisites_not_self_chk",
        ),
        Index("idx_course_corequisites_corequisite_course_id", "corequisite_course_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )
    course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("courses.course_id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    corequisite_course_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("courses.course_id", onupdate="CASCADE", ondelete="RESTRICT"),
        nullable=False,
    )

    course: Mapped[Course] = relationship(
        back_populates="corequisite_links",
        foreign_keys=[course_id],
    )
    corequisite_course: Mapped[Course] = relationship(
        back_populates="corequired_by_links",
        foreign_keys=[corequisite_course_id],
    )
