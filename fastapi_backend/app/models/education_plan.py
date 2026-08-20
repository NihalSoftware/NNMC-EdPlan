from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class EducationPlan(Base):
    __tablename__ = "education_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    program_name: Mapped[str] = mapped_column(String(256))
    university_name: Mapped[str] = mapped_column(String(256))
    degree: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped[User] = relationship(back_populates="education_plans")
    courses: Mapped[list[ProgramCourse]] = relationship(
        back_populates="education_plan", cascade="all, delete-orphan"
    )


class ProgramCourse(Base):
    __tablename__ = "program_courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    education_plan_id: Mapped[int] = mapped_column(
        ForeignKey("education_plans.id", ondelete="CASCADE"), index=True
    )
    year_label: Mapped[str | None] = mapped_column(String(64))
    semester_label: Mapped[str | None] = mapped_column(String(64))
    course_code: Mapped[str | None] = mapped_column(String(64))
    course_name: Mapped[str | None] = mapped_column(String(256))
    credits: Mapped[int | None] = mapped_column(Integer)
    prerequisite: Mapped[str | None] = mapped_column(String(256))
    corequisite: Mapped[str | None] = mapped_column(String(256))
    schedule: Mapped[dict | None] = mapped_column(JSON)

    education_plan: Mapped[EducationPlan] = relationship(back_populates="courses")


class CourseSchedule(Base):
    __tablename__ = "course_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    education_plan_id: Mapped[int] = mapped_column(
        ForeignKey("education_plans.id", ondelete="CASCADE"), index=True
    )
    course_id: Mapped[int] = mapped_column(ForeignKey("program_courses.id", ondelete="SET NULL"))
    day: Mapped[str | None] = mapped_column(String(32))
    time: Mapped[str | None] = mapped_column(String(32))
    available: Mapped[bool] = mapped_column(Boolean, default=True)


class CourseReschedule(Base):
    __tablename__ = "course_reschedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    payload: Mapped[dict] = mapped_column(JSON)

    user: Mapped[User] = relationship(back_populates="reschedules")


class Country(Base):
    __tablename__ = "countries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True)
    states: Mapped[list[State]] = relationship(back_populates="country", cascade="all")


class State(Base):
    __tablename__ = "states"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128))
    country_id: Mapped[int] = mapped_column(ForeignKey("countries.id"))

    country: Mapped[Country] = relationship(back_populates="states")
