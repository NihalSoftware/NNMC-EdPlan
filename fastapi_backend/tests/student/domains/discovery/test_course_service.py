import asyncio
import uuid

import pytest
from fastapi import HTTPException

from app.student.domains.discovery.services.course_service import CourseService


class _Repository:
    def __init__(self):
        self.calls = []
        self.course = {"course_id": str(uuid.uuid4()), "course_code": "CS 101"}
        self.dependencies = [{"course": {"course_code": "MATH 101"}}]

    async def list_courses(self, db, *, program_id=None, search=None):
        self.calls.append({"method": "list_courses", "program_id": program_id, "search": search})
        return [self.course]

    async def get_course_by_id(self, db, course_id):
        self.calls.append({"method": "get_course_by_id", "course_id": course_id})
        return self.course

    async def list_prerequisites(self, db, course_id):
        self.calls.append({"method": "list_prerequisites", "course_id": course_id})
        return self.dependencies

    async def list_corequisites(self, db, course_id):
        self.calls.append({"method": "list_corequisites", "course_id": course_id})
        return self.dependencies


def test_list_courses_delegates_clean_filters_to_repository():
    repository = _Repository()
    service = CourseService(repository)
    program_id = str(uuid.uuid4())

    result = asyncio.run(
        service.list_courses(
            object(),
            program_id=f" {program_id} ",
            search=" intro ",
        )
    )

    assert result == [repository.course]
    assert repository.calls == [
        {"method": "list_courses", "program_id": program_id, "search": "intro"}
    ]


def test_list_courses_rejects_invalid_program_uuid():
    repository = _Repository()
    service = CourseService(repository)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.list_courses(object(), program_id="not-a-uuid"))

    assert exc_info.value.status_code == 400
    assert repository.calls == []


def test_get_course_by_id_raises_404_when_missing():
    class _MissingRepository(_Repository):
        async def get_course_by_id(self, db, course_id):
            self.calls.append({"method": "get_course_by_id", "course_id": course_id})
            return None

    repository = _MissingRepository()
    service = CourseService(repository)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.get_course_by_id(object(), str(uuid.uuid4())))

    assert exc_info.value.status_code == 404


def test_list_prerequisites_rejects_invalid_course_uuid():
    repository = _Repository()
    service = CourseService(repository)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.list_prerequisites(object(), "not-a-uuid"))

    assert exc_info.value.status_code == 400
    assert repository.calls == []


def test_list_corequisites_delegates_to_repository():
    repository = _Repository()
    service = CourseService(repository)
    course_id = str(uuid.uuid4())

    result = asyncio.run(service.list_corequisites(object(), course_id))

    assert result == repository.dependencies
    assert repository.calls == [{"method": "list_corequisites", "course_id": course_id}]
