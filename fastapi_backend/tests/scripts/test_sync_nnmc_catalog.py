import copy
import json
import re
import uuid
from decimal import Decimal
from pathlib import Path

import pytest

from scripts import sync_nnmc_catalog as catalog_sync
from scripts.sync_nnmc_catalog import (
    _recommended_semester,
    _recommended_year,
    aggregate_program_courses,
    load_snapshot,
    program_credit_range,
    program_identity,
    reconcile,
    validate_snapshot,
)

SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "data" / "nnmc_catalog_2025_2026.json"


def test_authoritative_snapshot_is_complete():
    snapshot = load_snapshot(SNAPSHOT_PATH)

    assert len(snapshot["programs"]) == 66
    assert len(snapshot["courses"]) == 515
    assert sum(len(program["courses"]) for program in snapshot["programs"]) == 1_439
    assert (
        len(
            {
                str(course["coid"])
                for program in snapshot["programs"]
                for course in program["courses"]
            }
        )
        == 501
    )


def test_program_identity_uses_official_catalog_names_and_credentials():
    assert program_identity(
        {
            "title": "Associate Degree Nursing, AAS",
            "category": "Associate of Applied Science",
        }
    ) == ("Associate Degree Nursing", "Associate of Applied Science")
    assert program_identity(
        {"title": "RN to BSN", "category": "Bachelor of Science in Nursing"}
    ) == ("RN to BSN", "Bachelor of Science in Nursing")
    assert program_identity({"title": "Biotechnology, Certificate", "category": "Certificate"}) == (
        "Biotechnology",
        "Certificate",
    )
    assert program_identity(
        {
            "title": "Phlebotomy Technician Certificate",
            "category": "Certificate",
        }
    ) == ("Phlebotomy Technician", "Certificate")


def test_program_credit_range_preserves_rn_to_bsn_catalog_range():
    snapshot = load_snapshot(SNAPSHOT_PATH)
    program = next(program for program in snapshot["programs"] if program["poid"] == "178")

    assert program_credit_range(program) == (120.0, 122.0)


def test_duplicate_catalog_occurrences_are_preserved_per_course():
    snapshot = load_snapshot(SNAPSHOT_PATH)
    biology = next(program for program in snapshot["programs"] if program["title"] == "Biology, BS")

    aggregated = aggregate_program_courses(biology)

    assert len(biology["courses"]) == 107
    assert len(aggregated) == 81
    assert sum(len(occurrences) for occurrences in aggregated.values()) == 107


def test_exact_credit_ranges_and_fractional_hours_are_in_snapshot():
    snapshot = load_snapshot(SNAPSHOT_PATH)
    details = {course["code"]: course for course in snapshot["courses"]}

    assert details["ECED 4479L"]["creditsMin"] == 2
    assert details["ECED 4479L"]["creditsMax"] == 11
    assert details["NURS 1100L"]["labHours"] == 1.5


def test_ranged_math_course_code_and_title_match_the_official_catalog():
    snapshot = load_snapshot(SNAPSHOT_PATH)
    course = next(course for course in snapshot["courses"] if course["coid"] == "2768")

    assert course["code"] == "MATH 3400-3405"
    assert course["name"] == "Undergraduate Research Experience in Mathematics"
    assert course["catalogTitle"] == f'{course["code"]} - {course["name"]}'
    assert course["sourceUrl"].endswith("catoid=3&coid=2768")


def test_preserved_schedule_metadata_restores_default_plan_terms():
    metadata = {
        "recommended_year": "Third Year",
        "recommended_semester": "Spring",
    }

    assert _recommended_year(None, metadata, None) == 3
    assert _recommended_semester(None, metadata, None) == "Spring"


def test_official_schedule_takes_precedence_over_preserved_metadata():
    metadata = {
        "recommended_year": "First Year",
        "recommended_semester": "Fall",
    }

    assert _recommended_year(4, metadata, None) == 4
    assert _recommended_semester("Winter", metadata, None) == "Winter"


def test_duplicate_official_ids_are_rejected():
    snapshot = load_snapshot(SNAPSHOT_PATH)
    duplicate = copy.deepcopy(snapshot)
    duplicate["courses"].append(copy.deepcopy(duplicate["courses"][0]))

    with pytest.raises(ValueError, match="duplicate official course IDs"):
        validate_snapshot(duplicate)


class _FakeTransaction:
    def __init__(self, connection):
        self.connection = connection

    async def start(self):
        self.connection.staged = copy.deepcopy(self.connection.database)

    async def commit(self):
        self.connection.database.clear()
        self.connection.database.update(self.connection.staged)
        self.connection.staged = None

    async def rollback(self):
        self.connection.staged = None


class _FakeConnection:
    PROGRAM_COLUMNS = {
        "program_id",
        "university_id",
        "program_name",
        "degree",
        "total_credit_hours",
        "metadata_json",
    }
    COURSE_COLUMNS = {
        "course_id",
        "program_id",
        "course_code",
        "course_name",
        "credits",
        "lecture_hours",
        "lab_hours",
        "recommended_year",
        "recommended_semester",
        "description",
        "metadata_json",
        "source_sequence",
    }

    def __init__(self, database):
        self.database = database
        self.staged = None
        self.closed = False

    @property
    def data(self):
        return self.staged if self.staged is not None else self.database

    def transaction(self):
        return _FakeTransaction(self)

    async def fetchrow(self, statement, *_args):
        if "FROM universities" in statement:
            return {"university_id": self.database["university_id"]}
        raise AssertionError(statement)

    async def fetch(self, statement, *args):
        if "information_schema.columns" in statement:
            columns = self.PROGRAM_COLUMNS if args[0] == "programs" else self.COURSE_COLUMNS
            return [{"column_name": column} for column in sorted(columns)]
        if "FROM programs" in statement:
            return list(self.data["programs"].values())
        if "FROM courses" in statement:
            program_ids = set(args[0])
            return [
                row for row in self.data["courses"].values() if row["program_id"] in program_ids
            ]
        raise AssertionError(statement)

    async def executemany(self, statement, values):
        match = re.search(r"INSERT INTO (programs|courses) \(([^)]+)\)", statement)
        assert match is not None
        table_name = match.group(1)
        columns = [column.strip() for column in match.group(2).split(",")]
        primary_key = "program_id" if table_name == "programs" else "course_id"
        for value_row in values:
            row = dict(zip(columns, value_row, strict=True))
            if isinstance(row.get("metadata_json"), str):
                row["metadata_json"] = json.loads(row["metadata_json"])
            self.data[table_name][row[primary_key]] = row

    async def close(self):
        self.closed = True


class _FakeDatabase:
    def __init__(self):
        self.state = {
            "university_id": uuid.uuid4(),
            "programs": {},
            "courses": {},
        }
        self.connections = []

    async def connect(self, _dsn):
        connection = _FakeConnection(self.state)
        self.connections.append(connection)
        return connection


@pytest.mark.asyncio
async def test_sync_is_idempotent_and_failure_rolls_back(monkeypatch):
    snapshot = load_snapshot(SNAPSHOT_PATH)
    database = _FakeDatabase()
    monkeypatch.setattr(catalog_sync.asyncpg, "connect", database.connect)
    monkeypatch.setattr(catalog_sync.settings, "environment", "development")

    applied = await reconcile(snapshot, apply_changes=True)
    assert applied["programs"]["inserted"] == 66
    assert applied["courses"]["inserted"] == 1_250

    second_run = await reconcile(snapshot, apply_changes=False)
    assert second_run["pending_change_count"] == 0

    first_course = next(iter(database.state["courses"].values()))
    assert isinstance(first_course["credits"], Decimal)
    first_course["course_name"] = "intentionally stale"
    before_failure = copy.deepcopy(database.state)
    with pytest.raises(RuntimeError, match="Simulated catalog synchronization failure"):
        await reconcile(snapshot, apply_changes=True, simulate_failure=True)
    assert database.state == before_failure
    assert all(connection.closed for connection in database.connections)
