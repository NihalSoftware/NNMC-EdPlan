from __future__ import annotations

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.student.domains.planning.models import EdPlan, PlanCourse
from app.student.domains.scheduling.models import (
    AcademicTerm,
    CourseOffering,
    Section,
    SectionMeeting,
)
from app.student.domains.scheduling.repositories.retrieval_repository import (
    ScheduleRetrievalRepository,
    schedule_retrieval_repository,
)
from app.student.domains.scheduling.schemas.schedulepilot import (
    ScheduleCourse,
    ScheduleCourseOffering,
    ScheduleMeeting,
    ScheduleProgram,
    ScheduleRetrievalContext,
    ScheduleRetrievalWarnings,
    ScheduleSection,
    ScheduleStudentPlan,
    ScheduleTerm,
    ScheduleUniversity,
)


class SchedulePilotRetrievalError(Exception):
    """Base exception for deterministic SchedulePilot retrieval failures."""


class SchedulePilotPlanNotFoundError(SchedulePilotRetrievalError):
    """Raised when a plan does not exist or does not belong to the user."""


class SchedulePilotRetrievalService:
    """Builds read-only SchedulePilot context from normalized EdPlan tables."""

    def __init__(
        self,
        repository: ScheduleRetrievalRepository = schedule_retrieval_repository,
    ) -> None:
        self.repository = repository

    async def get_student_plan(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        plan_id: str | UUID,
    ) -> ScheduleStudentPlan:
        if user_id <= 0:
            raise ValueError("user_id must be greater than zero.")
        plan = await self.repository.get_student_plan(db, user_id=user_id, plan_id=plan_id)
        if plan is None:
            raise SchedulePilotPlanNotFoundError("Plan not found for the requested user.")
        return _student_plan_to_contract(plan)

    async def get_plan_courses(
        self,
        db: AsyncSession,
        *,
        plan_id: str | UUID,
    ) -> list[ScheduleCourse]:
        plan_courses = await self.repository.get_plan_courses(db, plan_id=plan_id)
        if plan_courses is None:
            raise ValueError("plan_id must be a valid UUID.")
        return [_plan_course_to_contract(plan_course) for plan_course in plan_courses]

    async def get_available_terms(self, db: AsyncSession) -> list[ScheduleTerm]:
        terms = await self.repository.get_active_terms(db)
        return [_term_to_contract(term) for term in terms]

    async def get_course_offerings(
        self,
        db: AsyncSession,
        *,
        course_ids: Sequence[str | UUID],
    ) -> list[ScheduleCourseOffering]:
        offerings = await self.repository.get_offerings_for_courses(db, course_ids=course_ids)
        return [_offering_to_contract(offering) for offering in offerings]

    async def get_course_sections(
        self,
        db: AsyncSession,
        *,
        offering_ids: Sequence[str | UUID],
    ) -> list[ScheduleSection]:
        sections = await self.repository.get_sections_for_offerings(db, offering_ids=offering_ids)
        return [_section_to_contract(section) for section in sections]

    async def get_section_meetings(
        self,
        db: AsyncSession,
        *,
        section_ids: Sequence[str | UUID],
    ) -> list[ScheduleMeeting]:
        meetings = await self.repository.get_meetings_for_sections(db, section_ids=section_ids)
        return [_meeting_to_contract(meeting) for meeting in meetings]

    async def build_context(
        self,
        db: AsyncSession,
        *,
        user_id: int,
        plan_id: str | UUID,
    ) -> ScheduleRetrievalContext:
        plan = await self.get_student_plan(db, user_id=user_id, plan_id=plan_id)
        courses = await self.get_plan_courses(db, plan_id=plan.plan_id)
        terms = await self.get_available_terms(db)
        offerings = await self.get_course_offerings(
            db,
            course_ids=[course.course_id for course in courses],
        )
        sections = await self.get_course_sections(
            db,
            offering_ids=[offering.offering_id for offering in offerings],
        )
        meetings = await self.get_section_meetings(
            db,
            section_ids=[section.section_id for section in sections],
        )
        return ScheduleRetrievalContext(
            plan=plan,
            courses=courses,
            terms=terms,
            offerings=offerings,
            sections=sections,
            meetings=meetings,
            warnings=_warnings(courses, offerings, sections, meetings),
        )


def _student_plan_to_contract(plan: EdPlan) -> ScheduleStudentPlan:
    return ScheduleStudentPlan(
        plan_id=str(plan.plan_id),
        user_id=plan.user_id,
        university_id=str(plan.university_id),
        program_id=str(plan.program_id),
        plan_name=plan.plan_name,
        description=plan.description,
        is_active=plan.is_active,
        created_at=plan.created_at,
        updated_at=plan.updated_at,
        university=(
            ScheduleUniversity(
                university_id=str(plan.university.university_id),
                university_name=plan.university.university_name,
                city=plan.university.city,
                state=plan.university.state,
                website=plan.university.website,
            )
            if plan.university is not None
            else None
        ),
        program=(
            ScheduleProgram(
                program_id=str(plan.program.program_id),
                program_name=plan.program.program_name,
                degree=plan.program.degree,
                total_credit_hours=plan.program.total_credit_hours,
            )
            if plan.program is not None
            else None
        ),
    )


def _plan_course_to_contract(plan_course: PlanCourse) -> ScheduleCourse:
    return ScheduleCourse(
        plan_course_id=str(plan_course.id),
        plan_id=str(plan_course.plan_id),
        course_id=str(plan_course.course_id),
        planned_term_id=str(plan_course.planned_term_id) if plan_course.planned_term_id else None,
        status=plan_course.status,
        notes=plan_course.notes,
        course_code=plan_course.course.course_code,
        course_name=plan_course.course.course_name,
        credits=float(plan_course.course.credits),
        lecture_hours=float(plan_course.course.lecture_hours),
        lab_hours=float(plan_course.course.lab_hours),
        recommended_year=plan_course.course.recommended_year,
        recommended_semester=plan_course.course.recommended_semester,
        planned_term=(
            _term_to_contract(plan_course.planned_term) if plan_course.planned_term else None
        ),
    )


def _term_to_contract(term: AcademicTerm) -> ScheduleTerm:
    return ScheduleTerm(
        term_id=str(term.term_id),
        term_name=term.term_name,
        start_date=term.start_date,
        end_date=term.end_date,
        is_active=term.is_active,
    )


def _offering_to_contract(offering: CourseOffering) -> ScheduleCourseOffering:
    return ScheduleCourseOffering(
        offering_id=str(offering.offering_id),
        course_id=str(offering.course_id),
        term_id=str(offering.term_id),
        offering_type=offering.offering_type,
        course_code=offering.course.course_code,
        course_name=offering.course.course_name,
        credits=float(offering.course.credits),
        term=_term_to_contract(offering.term),
    )


def _section_to_contract(section: Section) -> ScheduleSection:
    return ScheduleSection(
        section_id=str(section.section_id),
        offering_id=str(section.offering_id),
        course_id=str(section.offering.course_id),
        term_id=str(section.offering.term_id),
        offering_type=section.offering.offering_type,
        section_number=section.section_number,
        crn=section.crn,
        campus=section.campus,
        instructor=section.instructor,
        instruction_method=section.instruction_method,
        capacity=section.capacity,
        enrolled=section.enrolled,
        available_seats=max(0, section.capacity - section.enrolled),
        status=section.status,
    )


def _meeting_to_contract(meeting: SectionMeeting) -> ScheduleMeeting:
    is_async = (
        meeting.meeting_type == "Online Async"
        or meeting.weekday is None
        or meeting.start_time is None
        or meeting.end_time is None
    )
    return ScheduleMeeting(
        meeting_id=str(meeting.meeting_id),
        section_id=str(meeting.section_id),
        weekday=meeting.weekday,
        start_time=meeting.start_time,
        end_time=meeting.end_time,
        building=meeting.building,
        room=meeting.room,
        meeting_type=meeting.meeting_type,
        is_async=is_async,
    )


def _warnings(
    courses: list[ScheduleCourse],
    offerings: list[ScheduleCourseOffering],
    sections: list[ScheduleSection],
    meetings: list[ScheduleMeeting],
) -> ScheduleRetrievalWarnings:
    offered_course_ids = {offering.course_id for offering in offerings}
    section_offering_ids = {section.offering_id for section in sections}
    meeting_section_ids = {meeting.section_id for meeting in meetings}
    return ScheduleRetrievalWarnings(
        courses_without_offerings=[
            course.course_id for course in courses if course.course_id not in offered_course_ids
        ],
        offerings_without_sections=[
            offering.offering_id
            for offering in offerings
            if offering.offering_id not in section_offering_ids
        ],
        sections_without_meetings=[
            section.section_id
            for section in sections
            if section.section_id not in meeting_section_ids
        ],
    )


schedulepilot_retrieval_service = SchedulePilotRetrievalService()
