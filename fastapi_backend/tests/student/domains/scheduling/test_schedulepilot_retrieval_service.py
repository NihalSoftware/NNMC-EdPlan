from __future__ import annotations

import uuid
from datetime import date, datetime, time

import pytest

from app.student.domains.discovery.models import Course, Program, University
from app.student.domains.planning.models import EdPlan, PlanCourse
from app.student.domains.scheduling.models import (
    AcademicTerm,
    CourseOffering,
    Section,
    SectionMeeting,
)
from app.student.domains.scheduling.services.retrieval_service import (
    SchedulePilotPlanNotFoundError,
    SchedulePilotRetrievalService,
)


class _Repository:
    def __init__(
        self, *, plan=None, courses=None, terms=None, offerings=None, sections=None, meetings=None
    ):
        self.plan = plan
        self.courses = courses if courses is not None else []
        self.terms = terms if terms is not None else []
        self.offerings = offerings if offerings is not None else []
        self.sections = sections if sections is not None else []
        self.meetings = meetings if meetings is not None else []
        self.calls = []

    async def get_student_plan(self, db, *, user_id, plan_id):
        self.calls.append(("get_student_plan", user_id, plan_id))
        return self.plan

    async def get_plan_courses(self, db, *, plan_id):
        self.calls.append(("get_plan_courses", plan_id))
        return self.courses

    async def get_active_terms(self, db):
        self.calls.append(("get_active_terms",))
        return self.terms

    async def get_offerings_for_courses(self, db, *, course_ids):
        self.calls.append(("get_offerings_for_courses", list(course_ids)))
        return self.offerings

    async def get_sections_for_offerings(self, db, *, offering_ids, status="Open"):
        self.calls.append(("get_sections_for_offerings", list(offering_ids), status))
        return self.sections

    async def get_meetings_for_sections(self, db, *, section_ids):
        self.calls.append(("get_meetings_for_sections", list(section_ids)))
        return self.meetings


def _objects():
    university = University(
        university_id=uuid.uuid4(),
        university_name="Example University",
        city="Albuquerque",
        state="NM",
        website="https://example.edu",
    )
    program = Program(
        program_id=uuid.uuid4(),
        university_id=university.university_id,
        program_name="Computer Science",
        degree="BS",
        total_credit_hours=120,
        university=university,
    )
    course = Course(
        course_id=uuid.uuid4(),
        program_id=program.program_id,
        course_code="CS 101",
        course_name="Intro",
        credits=3,
        lecture_hours=3,
        lab_hours=0,
        recommended_year=1,
        recommended_semester="Fall",
        description=None,
        program=program,
    )
    term = AcademicTerm(
        term_id=uuid.uuid4(),
        term_name="Fall 2026",
        start_date=date(2026, 8, 17),
        end_date=date(2026, 12, 11),
        is_active=True,
    )
    plan = EdPlan(
        plan_id=uuid.uuid4(),
        user_id=1,
        university_id=university.university_id,
        program_id=program.program_id,
        plan_name="Primary Plan",
        description="Main path",
        is_active=True,
        created_at=datetime(2026, 6, 1),
        updated_at=datetime(2026, 6, 2),
        university=university,
        program=program,
    )
    plan_course = PlanCourse(
        id=uuid.uuid4(),
        plan_id=plan.plan_id,
        course_id=course.course_id,
        planned_term_id=term.term_id,
        status="Planned",
        notes="Take first.",
        plan=plan,
        course=course,
        planned_term=term,
    )
    offering = CourseOffering(
        offering_id=uuid.uuid4(),
        course_id=course.course_id,
        term_id=term.term_id,
        offering_type="Lecture",
        course=course,
        term=term,
    )
    section = Section(
        section_id=uuid.uuid4(),
        offering_id=offering.offering_id,
        section_number="001",
        crn="12345",
        campus="Main",
        instructor="Ada Lovelace",
        instruction_method="In Person",
        capacity=30,
        enrolled=10,
        status="Open",
        offering=offering,
    )
    meeting = SectionMeeting(
        meeting_id=uuid.uuid4(),
        section_id=section.section_id,
        weekday=1,
        start_time=time(9, 0),
        end_time=time(10, 15),
        building="SCI",
        room="101",
        meeting_type="Class",
        section=section,
    )
    return plan, plan_course, term, offering, section, meeting


@pytest.mark.asyncio
async def test_retrieval_service_builds_full_schedule_context():
    plan, plan_course, term, offering, section, meeting = _objects()
    repository = _Repository(
        plan=plan,
        courses=[plan_course],
        terms=[term],
        offerings=[offering],
        sections=[section],
        meetings=[meeting],
    )

    context = await SchedulePilotRetrievalService(repository).build_context(
        object(),
        user_id=1,
        plan_id=plan.plan_id,
    )

    assert context.plan.plan_id == str(plan.plan_id)
    assert context.courses[0].course_code == "CS 101"
    assert context.terms[0].term_name == "Fall 2026"
    assert context.offerings[0].offering_id == str(offering.offering_id)
    assert context.sections[0].available_seats == 20
    assert context.meetings[0].is_async is False
    assert context.warnings.courses_without_offerings == []
    assert repository.calls == [
        ("get_student_plan", 1, plan.plan_id),
        ("get_plan_courses", str(plan.plan_id)),
        ("get_active_terms",),
        ("get_offerings_for_courses", [str(plan_course.course_id)]),
        ("get_sections_for_offerings", [str(offering.offering_id)], "Open"),
        ("get_meetings_for_sections", [str(section.section_id)]),
    ]


@pytest.mark.asyncio
async def test_retrieval_service_validates_plan_ownership_by_repository_result():
    service = SchedulePilotRetrievalService(_Repository(plan=None))

    with pytest.raises(SchedulePilotPlanNotFoundError):
        await service.get_student_plan(object(), user_id=99, plan_id=str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_retrieval_service_handles_empty_plan_without_writes_or_failures():
    plan, _, term, _, _, _ = _objects()
    context = await SchedulePilotRetrievalService(
        _Repository(plan=plan, courses=[], terms=[term])
    ).build_context(object(), user_id=1, plan_id=plan.plan_id)

    assert context.courses == []
    assert context.offerings == []
    assert context.sections == []
    assert context.meetings == []
    assert context.warnings.courses_without_offerings == []


@pytest.mark.asyncio
async def test_retrieval_service_reports_missing_offerings_sections_and_meetings():
    plan, plan_course, term, offering, section, _ = _objects()
    no_offerings = await SchedulePilotRetrievalService(
        _Repository(plan=plan, courses=[plan_course], terms=[term])
    ).build_context(object(), user_id=1, plan_id=plan.plan_id)
    assert no_offerings.warnings.courses_without_offerings == [str(plan_course.course_id)]

    no_sections = await SchedulePilotRetrievalService(
        _Repository(plan=plan, courses=[plan_course], terms=[term], offerings=[offering])
    ).build_context(object(), user_id=1, plan_id=plan.plan_id)
    assert no_sections.warnings.offerings_without_sections == [str(offering.offering_id)]

    no_meetings = await SchedulePilotRetrievalService(
        _Repository(
            plan=plan,
            courses=[plan_course],
            terms=[term],
            offerings=[offering],
            sections=[section],
        )
    ).build_context(object(), user_id=1, plan_id=plan.plan_id)
    assert no_meetings.warnings.sections_without_meetings == [str(section.section_id)]
