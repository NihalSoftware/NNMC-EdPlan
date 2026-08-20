import asyncio
import uuid
from datetime import date, time

from app.student.domains.discovery.models import Course, Program, University
from app.student.domains.scheduling.models import (
    AcademicTerm,
    CourseOffering,
    Section,
    SectionMeeting,
)
from app.student.domains.scheduling.repositories.catalog_repository import (
    CourseOfferingRepository,
    SectionMeetingRepository,
    SectionRepository,
    TermRepository,
)
from app.student.domains.scheduling.repositories.retrieval_repository import (
    ScheduleRetrievalRepository,
)


class _ScalarResult:
    def __init__(self, values):
        self._values = values

    def all(self):
        return self._values


class _Result:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return _ScalarResult(self._values)

    def scalar_one_or_none(self):
        return self._values[0] if self._values else None


class _Session:
    def __init__(self, values):
        self.values = values
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return _Result(self.values)


def _term():
    return AcademicTerm(
        term_id=uuid.uuid4(),
        term_name="Fall 2026",
        start_date=date(2026, 8, 17),
        end_date=date(2026, 12, 11),
        is_active=True,
    )


def _course():
    university = University(
        university_id=uuid.uuid4(),
        university_name="Northern New Mexico College",
        city="Espanola",
        state="New Mexico",
        website="https://www.nnmc.edu/",
    )
    program = Program(
        program_id=uuid.uuid4(),
        university_id=university.university_id,
        program_name="Computer Science",
        degree="Bachelor of Science",
        total_credit_hours=120,
        university=university,
    )
    return Course(
        course_id=uuid.uuid4(),
        program_id=program.program_id,
        course_code="CS 101",
        course_name="Intro to Computer Science",
        credits=3,
        lecture_hours=3,
        lab_hours=0,
        recommended_year=1,
        recommended_semester="Fall",
        description="Foundational course.",
        program=program,
    )


def _offering():
    term = _term()
    course = _course()
    return CourseOffering(
        offering_id=uuid.uuid4(),
        course_id=course.course_id,
        term_id=term.term_id,
        offering_type="Lecture",
        course=course,
        term=term,
    )


def _section():
    offering = _offering()
    return Section(
        section_id=uuid.uuid4(),
        offering_id=offering.offering_id,
        section_number="001",
        crn="12345",
        campus="Main",
        instructor="Ada Lovelace",
        instruction_method="In Person",
        capacity=30,
        enrolled=12,
        status="Open",
        offering=offering,
    )


def test_term_repository_lists_terms():
    term = _term()
    repository = TermRepository()
    session = _Session([term])

    result = asyncio.run(repository.list_terms(session))

    assert result == [
        {
            "term_id": str(term.term_id),
            "term_name": "Fall 2026",
            "start_date": date(2026, 8, 17),
            "end_date": date(2026, 12, 11),
            "is_active": True,
        }
    ]
    assert len(session.statements) == 1


def test_term_repository_rejects_invalid_uuid_without_query():
    repository = TermRepository()
    session = _Session([_term()])

    result = asyncio.run(repository.get_term_by_id(session, "not-a-uuid"))

    assert result is None
    assert session.statements == []


def test_offering_repository_lists_course_offerings():
    offering = _offering()
    repository = CourseOfferingRepository()
    session = _Session([offering])

    result = asyncio.run(repository.list_offerings_by_course(session, str(offering.course_id)))

    assert result[0]["offering_id"] == str(offering.offering_id)
    assert result[0]["course"]["course_code"] == "CS 101"
    assert result[0]["term"]["term_name"] == "Fall 2026"
    assert len(session.statements) == 1


def test_section_repository_returns_section_detail_with_offering():
    section = _section()
    repository = SectionRepository()
    session = _Session([section])

    result = asyncio.run(repository.get_section_by_id(session, str(section.section_id)))

    assert result["section_id"] == str(section.section_id)
    assert result["offering"]["offering_id"] == str(section.offering_id)
    assert result["offering"]["term"]["term_name"] == "Fall 2026"


def test_section_meeting_repository_lists_meetings():
    section = _section()
    meeting = SectionMeeting(
        meeting_id=uuid.uuid4(),
        section_id=section.section_id,
        weekday=1,
        start_time=time(9, 0),
        end_time=time(10, 15),
        building="Science",
        room="101",
        meeting_type="Class",
        section=section,
    )
    repository = SectionMeetingRepository()
    session = _Session([meeting])

    result = asyncio.run(repository.list_meetings_by_section(session, str(section.section_id)))

    assert result == [
        {
            "meeting_id": str(meeting.meeting_id),
            "section_id": str(section.section_id),
            "weekday": 1,
            "start_time": time(9, 0),
            "end_time": time(10, 15),
            "building": "Science",
            "room": "101",
            "meeting_type": "Class",
        }
    ]
    assert len(session.statements) == 1


def test_schedule_retrieval_repository_uses_batch_offering_lookup():
    offering = _offering()
    repository = ScheduleRetrievalRepository()
    session = _Session([offering])

    result = asyncio.run(
        repository.get_offerings_for_courses(
            session,
            course_ids=[str(offering.course_id), str(offering.course_id)],
        )
    )

    assert result == [offering]
    assert len(session.statements) == 1


def test_schedule_retrieval_repository_uses_batch_section_lookup():
    section = _section()
    repository = ScheduleRetrievalRepository()
    session = _Session([section])

    result = asyncio.run(
        repository.get_sections_for_offerings(
            session,
            offering_ids=[str(section.offering_id)],
        )
    )

    assert result == [section]
    assert len(session.statements) == 1


def test_schedule_retrieval_repository_uses_batch_meeting_lookup():
    section = _section()
    meeting = SectionMeeting(
        meeting_id=uuid.uuid4(),
        section_id=section.section_id,
        weekday=None,
        start_time=None,
        end_time=None,
        building=None,
        room=None,
        meeting_type="Online Async",
        section=section,
    )
    repository = ScheduleRetrievalRepository()
    session = _Session([meeting])

    result = asyncio.run(
        repository.get_meetings_for_sections(
            session,
            section_ids=[str(section.section_id)],
        )
    )

    assert result == [meeting]
    assert len(session.statements) == 1


def test_schedule_retrieval_repository_empty_batches_do_not_query():
    repository = ScheduleRetrievalRepository()
    session = _Session([])

    offerings = asyncio.run(repository.get_offerings_for_courses(session, course_ids=[]))
    sections = asyncio.run(repository.get_sections_for_offerings(session, offering_ids=[]))
    meetings = asyncio.run(repository.get_meetings_for_sections(session, section_ids=[]))

    assert offerings == []
    assert sections == []
    assert meetings == []
    assert session.statements == []
