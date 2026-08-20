import asyncio
import uuid

import pytest
from fastapi import HTTPException

from app.student.domains.scheduling.services.catalog_service import (
    CourseOfferingService,
    SectionMeetingService,
    SectionService,
    TermService,
)


class _TermRepository:
    def __init__(self):
        self.calls = []
        self.term = {"term_id": str(uuid.uuid4()), "term_name": "Fall 2026"}

    async def list_terms(self, db):
        self.calls.append({"method": "list_terms"})
        return [self.term]

    async def get_term_by_id(self, db, term_id):
        self.calls.append({"method": "get_term_by_id", "term_id": term_id})
        return self.term


class _OfferingRepository:
    def __init__(self):
        self.calls = []
        self.offering = {"offering_id": str(uuid.uuid4()), "offering_type": "Lecture"}

    async def list_offerings_by_course(self, db, course_id):
        self.calls.append({"method": "list_offerings_by_course", "course_id": course_id})
        return [self.offering]

    async def get_offering_by_id(self, db, offering_id):
        self.calls.append({"method": "get_offering_by_id", "offering_id": offering_id})
        return self.offering


class _SectionRepository:
    def __init__(self):
        self.calls = []
        self.section = {"section_id": str(uuid.uuid4()), "section_number": "001"}

    async def list_sections_by_offering(self, db, offering_id):
        self.calls.append({"method": "list_sections_by_offering", "offering_id": offering_id})
        return [self.section]

    async def get_section_by_id(self, db, section_id):
        self.calls.append({"method": "get_section_by_id", "section_id": section_id})
        return self.section


class _MeetingRepository:
    def __init__(self):
        self.calls = []
        self.meeting = {"meeting_id": str(uuid.uuid4()), "meeting_type": "Class"}

    async def list_meetings_by_section(self, db, section_id):
        self.calls.append({"method": "list_meetings_by_section", "section_id": section_id})
        return [self.meeting]


def test_term_service_lists_terms():
    repository = _TermRepository()
    service = TermService(repository)

    result = asyncio.run(service.list_terms(object()))

    assert result == [repository.term]
    assert repository.calls == [{"method": "list_terms"}]


def test_term_service_rejects_invalid_uuid():
    repository = _TermRepository()
    service = TermService(repository)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.get_term_by_id(object(), "not-a-uuid"))

    assert exc_info.value.status_code == 400
    assert repository.calls == []


def test_offering_service_delegates_course_offering_lookup():
    repository = _OfferingRepository()
    service = CourseOfferingService(repository)
    course_id = str(uuid.uuid4())

    result = asyncio.run(service.list_offerings_by_course(object(), course_id))

    assert result == [repository.offering]
    assert repository.calls == [{"method": "list_offerings_by_course", "course_id": course_id}]


def test_offering_service_raises_404_when_missing():
    class _MissingRepository(_OfferingRepository):
        async def get_offering_by_id(self, db, offering_id):
            self.calls.append({"method": "get_offering_by_id", "offering_id": offering_id})
            return None

    repository = _MissingRepository()
    service = CourseOfferingService(repository)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.get_offering_by_id(object(), str(uuid.uuid4())))

    assert exc_info.value.status_code == 404


def test_section_service_delegates_section_lookup():
    repository = _SectionRepository()
    service = SectionService(repository)
    section_id = str(uuid.uuid4())

    result = asyncio.run(service.get_section_by_id(object(), section_id))

    assert result == repository.section
    assert repository.calls == [{"method": "get_section_by_id", "section_id": section_id}]


def test_section_meeting_service_delegates_meeting_lookup():
    repository = _MeetingRepository()
    service = SectionMeetingService(repository)
    section_id = str(uuid.uuid4())

    result = asyncio.run(service.list_meetings_by_section(object(), section_id))

    assert result == [repository.meeting]
    assert repository.calls == [{"method": "list_meetings_by_section", "section_id": section_id}]


def test_section_meeting_service_rejects_invalid_uuid():
    repository = _MeetingRepository()
    service = SectionMeetingService(repository)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.list_meetings_by_section(object(), "not-a-uuid"))

    assert exc_info.value.status_code == 400
    assert repository.calls == []
