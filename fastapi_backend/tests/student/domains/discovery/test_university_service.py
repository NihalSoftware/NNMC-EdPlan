import asyncio
import uuid

import pytest
from fastapi import HTTPException

from app.student.domains.discovery.services.university_service import UniversityService


class _Repository:
    def __init__(self):
        self.calls = []
        self.university = {
            "university_id": str(uuid.uuid4()),
            "unit_id": str(uuid.uuid4()),
            "name": "Northern New Mexico College",
        }

    async def list_universities(self, db, *, search=None, state=None, offset=0, limit=20):
        self.calls.append(
            {
                "method": "list_universities",
                "search": search,
                "state": state,
                "offset": offset,
                "limit": limit,
            }
        )
        return [self.university]

    async def get_university_by_id(self, db, university_id):
        self.calls.append({"method": "get_university_by_id", "university_id": university_id})
        return self.university

    async def get_universities_by_ids(self, db, university_ids):
        self.calls.append({"method": "get_universities_by_ids", "university_ids": university_ids})
        return [self.university]


class _NoMatchScorecard:
    async def get_school(self, unit_id):
        return None

    async def find_schools_by_profiles(self, profiles):
        return [None] * len(profiles)

    async def find_school_by_profile(self, **kwargs):
        return None


class _MatchingScorecard:
    async def get_school(self, unit_id):
        return await self.find_school_by_profile()

    async def find_schools_by_profiles(self, profiles):
        return [await self.find_school_by_profile() for _ in profiles]

    async def find_school_by_profile(self, **kwargs):
        return {
            "unit_id": 188058,
            "scorecard_unit_id": 188058,
            "size": 926,
            "graduation_rate": 0.2967,
            "average_annual_cost": 7276,
            "typical_earnings": 38112,
            "financial_aid_debt": 6000,
            "open_admissions_policy": True,
        }


def test_search_universities_returns_results_and_metadata():
    repository = _Repository()
    service = UniversityService(repository, _NoMatchScorecard())

    result = asyncio.run(
        service.search_universities(
            object(),
            search=" Northern New Mexico College ",
            state=" NM ",
            page=2,
            per_page=10,
        )
    )

    assert result["results"] == [repository.university]
    assert result["metadata"] == {
        "count": 1,
        "page": 2,
        "per_page": 10,
        "source": "Northern New Mexico College catalog and College Scorecard",
    }
    assert repository.calls == [
        {
            "method": "list_universities",
            "search": "Northern New Mexico College",
            "state": "NM",
            "offset": 20,
            "limit": 10,
        }
    ]


def test_search_universities_enriches_cards_with_scorecard_data():
    repository = _Repository()
    service = UniversityService(repository, _MatchingScorecard())

    result = asyncio.run(service.search_universities(object()))

    school = result["results"][0]
    assert school["unit_id"] == repository.university["unit_id"]
    assert school["scorecard_unit_id"] == 188058
    assert school["size"] == 926
    assert school["graduation_rate"] == 0.2967
    assert school["average_annual_cost"] == 7276
    assert school["typical_earnings"] == 38112
    assert school["financial_aid_debt"] == 6000
    assert school["open_admissions_policy"] is True


def test_get_university_rejects_invalid_uuid():
    repository = _Repository()
    service = UniversityService(repository)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.get_university(object(), "not-a-uuid"))

    assert exc_info.value.status_code == 400
    assert repository.calls == []


def test_get_university_raises_404_when_missing():
    class _MissingRepository(_Repository):
        async def get_university_by_id(self, db, university_id):
            self.calls.append({"method": "get_university_by_id", "university_id": university_id})
            return None

    repository = _MissingRepository()
    service = UniversityService(repository)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.get_university(object(), str(uuid.uuid4())))

    assert exc_info.value.status_code == 404


def test_compare_universities_requires_two_valid_uuid_values():
    repository = _Repository()
    service = UniversityService(repository)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.compare_universities(object(), [str(uuid.uuid4())]))

    assert exc_info.value.status_code == 400
    assert repository.calls == []


def test_compare_universities_is_disabled_for_single_institution_site():
    repository = _Repository()
    service = UniversityService(repository, _NoMatchScorecard())
    ids = [str(uuid.uuid4()) for _ in range(6)]

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(service.compare_universities(object(), ids))

    assert exc_info.value.status_code == 400
    assert "Northern New Mexico College" in exc_info.value.detail
    assert repository.calls == []
