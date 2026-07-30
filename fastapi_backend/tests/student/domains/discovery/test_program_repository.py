import asyncio
import uuid

from app.student.domains.discovery.models import Program, University
from app.student.domains.discovery.repositories.program_repository import ProgramRepository


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


def _program(
    *,
    program_id=None,
    university_id=None,
    program_name="Computer Science",
    degree="Bachelor of Science",
):
    university = University(
        university_id=university_id or uuid.uuid4(),
        university_name="Northern New Mexico College",
        city="Espanola",
        state="New Mexico",
        website="https://www.nnmc.edu/",
    )
    return Program(
        program_id=program_id or uuid.uuid4(),
        university_id=university.university_id,
        program_name=program_name,
        degree=degree,
        total_credit_hours=120,
        university=university,
    )


def test_get_programs_returns_program_summaries():
    program = _program()
    repository = ProgramRepository()
    session = _Session([program])

    result = asyncio.run(repository.get_programs(session))

    assert result == [
        {
            "program_id": str(program.program_id),
            "program_name": "Computer Science",
            "degree": "Bachelor of Science",
            "total_credit_hours": 120,
            "catalog_title": None,
            "catalog_url": None,
            "catalog_year": None,
            "description": None,
            "metadata_json": {},
            "university": {
                "university_id": str(program.university.university_id),
                "university_name": "Northern New Mexico College",
                "city": "Espanola",
                "state": "New Mexico",
                "website": "https://www.nnmc.edu/",
            },
        }
    ]
    assert len(session.statements) == 1


def test_get_program_by_id_returns_one_program():
    program_id = uuid.uuid4()
    program = _program(program_id=program_id)
    repository = ProgramRepository()
    session = _Session([program])

    result = asyncio.run(repository.get_program_by_id(session, str(program_id)))

    assert result["program_id"] == str(program_id)
    assert result["program_name"] == "Computer Science"


def test_get_program_by_id_rejects_invalid_uuid_without_query():
    repository = ProgramRepository()
    session = _Session([_program()])

    result = asyncio.run(repository.get_program_by_id(session, "not-a-uuid"))

    assert result is None
    assert session.statements == []


def test_search_programs_returns_matching_programs():
    program = _program(program_name="Nursing", degree="Bachelor of Science in Nursing")
    repository = ProgramRepository()
    session = _Session([program])

    result = asyncio.run(repository.search_programs(session, "nursing"))

    assert result[0]["program_name"] == "Nursing"
    assert len(session.statements) == 1


def test_get_programs_by_university_filters_by_uuid():
    university_id = uuid.uuid4()
    program = _program(university_id=university_id)
    repository = ProgramRepository()
    session = _Session([program])

    result = asyncio.run(repository.get_programs_by_university(session, str(university_id)))

    assert result[0]["university"]["university_id"] == str(university_id)
    assert len(session.statements) == 1


def test_get_programs_by_university_rejects_invalid_uuid_without_query():
    repository = ProgramRepository()
    session = _Session([_program()])

    result = asyncio.run(repository.get_programs_by_university(session, "not-a-uuid"))

    assert result == []
    assert session.statements == []
