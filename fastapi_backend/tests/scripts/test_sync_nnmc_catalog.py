from pathlib import Path

from scripts.sync_nnmc_catalog import (
    _recommended_semester,
    _recommended_year,
    aggregate_program_courses,
    load_snapshot,
    program_identity,
)

SNAPSHOT_PATH = Path(__file__).resolve().parents[2] / "data" / "nnmc_catalog_2025_2026.json"


def test_authoritative_snapshot_is_complete():
    snapshot = load_snapshot(SNAPSHOT_PATH)

    assert len(snapshot["programs"]) == 66
    assert len(snapshot["courses"]) == 501
    assert sum(len(program["courses"]) for program in snapshot["programs"]) == 1_439


def test_program_identity_matches_stable_database_names():
    assert program_identity(
        {
            "title": "Associate Degree Nursing, AAS",
            "category": "Associate of Applied Science",
        }
    ) == ("Nursing", "Associate")
    assert program_identity(
        {"title": "RN to BSN", "category": "Bachelor of Science in Nursing"}
    ) == ("RN to BSN", "Bachelors")
    assert program_identity({"title": "Biotechnology, Certificate", "category": "Certificate"}) == (
        "Biotechnology",
        "Certificate",
    )


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
