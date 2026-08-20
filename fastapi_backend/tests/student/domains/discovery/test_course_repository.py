import asyncio
import uuid

from app.student.domains.discovery.models import (
    Course,
    CourseCorequisite,
    CoursePrerequisite,
    Program,
    University,
)
from app.student.domains.discovery.repositories.course_repository import CourseRepository


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


def _program():
    university = University(
        university_id=uuid.uuid4(),
        university_name="Northern New Mexico College",
        city="Espanola",
        state="New Mexico",
        website="https://www.nnmc.edu/",
    )
    return Program(
        program_id=uuid.uuid4(),
        university_id=university.university_id,
        program_name="Computer Science",
        degree="Bachelor of Science",
        total_credit_hours=120,
        university=university,
    )


def _course(program, *, code="CS 101", name="Intro to Computer Science"):
    return Course(
        course_id=uuid.uuid4(),
        program_id=program.program_id,
        course_code=code,
        course_name=name,
        credits=3,
        lecture_hours=3,
        lab_hours=0,
        recommended_year=1,
        recommended_semester="Fall",
        description="Foundational catalog course.",
        program=program,
    )


def test_list_courses_returns_course_summaries():
    program = _program()
    course = _course(program)
    repository = CourseRepository()
    session = _Session([course])

    result = asyncio.run(repository.list_courses(session, program_id=str(program.program_id)))

    assert result[0]["course_id"] == str(course.course_id)
    assert result[0]["program_id"] == str(program.program_id)
    assert result[0]["course_code"] == "CS 101"
    assert result[0]["code"] == "CS 101"
    assert result[0]["recommended_year"] == 1
    assert result[0]["semester"] == "Fall"
    assert len(session.statements) == 1


def test_get_course_by_id_returns_program_and_dependencies():
    program = _program()
    course = _course(program)
    prerequisite = _course(program, code="MATH 101", name="College Algebra")
    corequisite = _course(program, code="CS 101L", name="Intro Lab")
    prerequisite_link = CoursePrerequisite(
        id=uuid.uuid4(),
        course_id=course.course_id,
        prerequisite_course_id=prerequisite.course_id,
        course=course,
        prerequisite_course=prerequisite,
    )
    corequisite_link = CourseCorequisite(
        id=uuid.uuid4(),
        course_id=course.course_id,
        corequisite_course_id=corequisite.course_id,
        course=course,
        corequisite_course=corequisite,
    )
    course.prerequisite_links = [prerequisite_link]
    course.corequisite_links = [corequisite_link]
    repository = CourseRepository()
    session = _Session([course])

    result = asyncio.run(repository.get_course_by_id(session, str(course.course_id)))

    assert result["program"]["program_name"] == "Computer Science"
    assert result["prerequisites"][0]["prerequisite_course_id"] == str(prerequisite.course_id)
    assert result["prerequisites"][0]["course"]["course_code"] == "MATH 101"
    assert result["corequisites"][0]["corequisite_course_id"] == str(corequisite.course_id)
    assert result["corequisites"][0]["course"]["course_code"] == "CS 101L"


def test_list_prerequisites_returns_dependency_links():
    program = _program()
    course = _course(program)
    prerequisite = _course(program, code="MATH 101", name="College Algebra")
    link = CoursePrerequisite(
        id=uuid.uuid4(),
        course_id=course.course_id,
        prerequisite_course_id=prerequisite.course_id,
        prerequisite_course=prerequisite,
    )
    repository = CourseRepository()
    session = _Session([link])

    result = asyncio.run(repository.list_prerequisites(session, str(course.course_id)))

    assert result[0]["prerequisite_course_id"] == str(prerequisite.course_id)
    assert result[0]["course"]["course_name"] == "College Algebra"


def test_list_corequisites_rejects_invalid_uuid_without_query():
    repository = CourseRepository()
    session = _Session([])

    result = asyncio.run(repository.list_corequisites(session, "not-a-uuid"))

    assert result is None
    assert session.statements == []
