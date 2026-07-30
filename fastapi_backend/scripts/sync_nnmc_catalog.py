"""Reconcile the checked-in NNMC catalog snapshot with PostgreSQL.

The command is a dry run unless ``--apply`` is supplied. Existing program and
course identifiers are deliberately preserved because saved education plans
refer to them. Rows that are not present in the current catalog are retained
and marked inactive in ``metadata_json``.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import asyncpg
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.shared.constants.institution import (  # noqa: E402
    NORTHERN_NEW_MEXICO_COLLEGE_NAME,
)

DEFAULT_SNAPSHOT = BACKEND_ROOT / "data" / "nnmc_catalog_2025_2026.json"
EXPECTED_PROGRAMS = 66
EXPECTED_UNIQUE_COURSES = 501
EXPECTED_PROGRAM_COURSE_OCCURRENCES = 1_439
VERIFIED_ON = "2026-07-28"
YEAR_NUMBER_BY_LABEL = {
    "first year": 1,
    "second year": 2,
    "third year": 3,
    "fourth year": 4,
    "fifth year": 5,
    "sixth year": 6,
    "seventh year": 7,
    "eighth year": 8,
}

PROGRAM_IDENTITY_OVERRIDES = {
    "Electrical Technology, AAS": ("Electrical Technology", "Associate"),
    "General Psychology, AA": ("General Psychology", "Associate"),
    "Information Engineering Technology, AEng": (
        "Information Engineering Technology",
        "Associate",
    ),
    "Nuclear Operations Technology, AAS": (
        "Nuclear Operations Technology",
        "Associate",
    ),
    "Associate Degree Nursing, AAS": ("Nursing", "Associate"),
    "Plumbing Non-Apprenticeship, AAS": (
        "Plumbing Non-Apprenticeship",
        "Associate",
    ),
    "Software Engineering, AEng": ("Software Engineering", "Associate"),
    "RN to BSN": ("RN to BSN", "Bachelors"),
    "Self-Design, BAIS": ("Self-Design", "Bachelors"),
    "Phlebotomy Technician Certificate": ("Phlebotomy", "Certificate"),
}


def load_snapshot(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as snapshot_file:
        snapshot = json.load(snapshot_file)
    validate_snapshot(snapshot)
    return snapshot


def validate_snapshot(snapshot: dict[str, Any]) -> None:
    programs = snapshot.get("programs") or []
    courses = snapshot.get("courses") or []
    occurrence_count = sum(len(program.get("courses") or []) for program in programs)

    errors: list[str] = []
    if len(programs) != EXPECTED_PROGRAMS:
        errors.append(f"expected {EXPECTED_PROGRAMS} programs, found {len(programs)}")
    if len(courses) != EXPECTED_UNIQUE_COURSES:
        errors.append(f"expected {EXPECTED_UNIQUE_COURSES} unique courses, found {len(courses)}")
    if occurrence_count != EXPECTED_PROGRAM_COURSE_OCCURRENCES:
        errors.append(
            "expected "
            f"{EXPECTED_PROGRAM_COURSE_OCCURRENCES} program-course occurrences, "
            f"found {occurrence_count}"
        )

    course_ids = {str(course.get("coid") or "") for course in courses}
    missing_details = sorted(
        {
            str(occurrence.get("coid") or "")
            for program in programs
            for occurrence in program.get("courses") or []
            if str(occurrence.get("coid") or "") not in course_ids
        }
    )
    if missing_details:
        errors.append(f"missing course details for catalog IDs: {missing_details[:10]}")

    incomplete_courses = [
        str(course.get("coid") or "unknown")
        for course in courses
        if not course.get("code")
        or not course.get("name")
        or not (course.get("fields") or {}).get("description")
        or course.get("creditsMin") is None
    ]
    if incomplete_courses:
        errors.append(f"incomplete course records: {incomplete_courses[:10]}")

    incomplete_programs = [
        str(program.get("title") or "unknown")
        for program in programs
        if not program.get("title")
        or not program.get("sourceUrl")
        or not program.get("totalCredits")
        or not program.get("courses")
    ]
    if incomplete_programs:
        errors.append(f"incomplete program records: {incomplete_programs[:10]}")

    if errors:
        raise ValueError("Invalid NNMC catalog snapshot: " + "; ".join(errors))


def program_identity(program: dict[str, Any]) -> tuple[str, str]:
    title = str(program["title"]).strip()
    if title in PROGRAM_IDENTITY_OVERRIDES:
        return PROGRAM_IDENTITY_OVERRIDES[title]

    category = str(program["category"]).strip()
    if category == "Certificate":
        name = re.sub(r",?\s+Certificate$", "", title).strip()
        return name, category

    name = re.sub(r",\s*(?:BA|BS|BAIS|BBA|BEng|AA|AS|AAS|AEng)$", "", title).strip()
    return name, category


def aggregate_program_courses(
    program: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    occurrences: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for occurrence in program.get("courses") or []:
        occurrences[str(occurrence["coid"])].append(occurrence)
    return dict(occurrences)


def _canonical_code(value: Any) -> str:
    return " ".join(str(value or "").upper().split())


def _first_reported(occurrences: list[dict[str, Any]], key: str) -> Any:
    return next((occurrence.get(key) for occurrence in occurrences if occurrence.get(key)), None)


def _recommended_year(
    official_value: Any,
    existing_metadata: dict[str, Any],
    existing_value: int | None,
) -> int | None:
    if official_value is not None:
        return int(official_value)
    metadata_value = existing_metadata.get("recommended_year")
    if isinstance(metadata_value, int):
        return metadata_value
    if metadata_value:
        normalized = str(metadata_value).strip().lower()
        if normalized in YEAR_NUMBER_BY_LABEL:
            return YEAR_NUMBER_BY_LABEL[normalized]
        match = re.search(r"\d+", normalized)
        if match:
            return int(match.group())
    return existing_value


def _recommended_semester(
    official_value: Any,
    existing_metadata: dict[str, Any],
    existing_value: str | None,
) -> str | None:
    if official_value:
        return str(official_value)
    metadata_value = existing_metadata.get("recommended_semester")
    if metadata_value in {"Fall", "Spring", "Summer", "Winter"}:
        return str(metadata_value)
    return existing_value


def _storage_hours(value: Any, existing_value: int | None) -> int:
    """Return a compatible integer while exact source values live in metadata."""
    if isinstance(value, (int, float)) and float(value).is_integer():
        return int(value)
    if existing_value is not None:
        return int(existing_value)
    return 0


def _merge_metadata(existing: dict[str, Any] | None, updates: dict[str, Any]) -> dict:
    return {**(existing or {}), **updates}


def _program_metadata(
    existing: dict[str, Any] | None,
    program: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict:
    return _merge_metadata(
        existing,
        {
            "is_current_catalog": True,
            "catalog_year": snapshot["catalogYear"],
            "catalog_title": program["catalogTitle"],
            "catalog_url": program["sourceUrl"],
            "catalog_program_id": str(program["poid"]),
            "catalog_category": program["category"],
            "catalog_intro": program.get("intro") or [],
            "catalog_headings": program.get("headings") or [],
            "catalog_requirement_groups": program.get("requirementGroups") or [],
            "catalog_total_credits_text": program.get("totalCreditsText"),
            "catalog_source": snapshot["source"],
            "verified_on": VERIFIED_ON,
        },
    )


def _course_metadata(
    existing: dict[str, Any] | None,
    detail: dict[str, Any],
    occurrences: list[dict[str, Any]],
    snapshot: dict[str, Any],
) -> dict:
    fields = detail.get("fields") or {}
    normalized_occurrences = [
        {
            "sequence": occurrence.get("sequence"),
            "requirement_path": occurrence.get("requirementPath") or [],
            "group_text": occurrence.get("groupText"),
            "credit_text": occurrence.get("creditText"),
            "is_elective": occurrence.get("isElective") is True,
            "recommended_year": occurrence.get("recommendedYear"),
            "recommended_semester": occurrence.get("recommendedSemester"),
        }
        for occurrence in sorted(occurrences, key=lambda item: item.get("sequence") or 0)
    ]
    is_elective = bool(normalized_occurrences) and all(
        occurrence["is_elective"] for occurrence in normalized_occurrences
    )
    return _merge_metadata(
        existing,
        {
            "is_current_catalog": True,
            "catalog_year": snapshot["catalogYear"],
            "catalog_course_id": str(detail["coid"]),
            "catalog_course_title": detail["catalogTitle"],
            "catalog_url": detail["sourceUrl"],
            "catalog_source": snapshot["source"],
            "catalog_credit_text": _first_reported(occurrences, "creditText"),
            "credit_contact_text": detail.get("creditContactText"),
            "credits_min": detail.get("creditsMin"),
            "credits_max": detail.get("creditsMax"),
            "lecture_hours_exact": detail.get("lectureHours"),
            "lab_hours_exact": detail.get("labHours"),
            "fields": fields,
            "field_links": detail.get("fieldLinks") or {},
            "prerequisite": fields.get("prerequisites"),
            "corequisite": fields.get("corequisites"),
            "prerequisites_or_corequisites": fields.get("prerequisites_or_corequisites"),
            "cross_listed_as": fields.get("cross_listed_as"),
            "requirement_occurrences": normalized_occurrences,
            "is_elective": is_elective,
            "verified_on": VERIFIED_ON,
        },
    )


async def reconcile(snapshot: dict[str, Any], *, apply_changes: bool) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "mode": "apply" if apply_changes else "dry-run",
        "programs_verified": 0,
        "programs_added": 0,
        "programs_marked_inactive": 0,
        "courses_verified": 0,
        "courses_added": 0,
        "courses_marked_inactive": 0,
        "program_course_occurrences": EXPECTED_PROGRAM_COURSE_OCCURRENCES,
        "unique_catalog_courses": EXPECTED_UNIQUE_COURSES,
    }

    course_details = {str(course["coid"]): course for course in snapshot["courses"]}
    database_url = make_url(settings.database_url)
    dsn = database_url.set(drivername="postgresql").render_as_string(hide_password=False)
    connection = await asyncpg.connect(dsn)

    try:
        transaction = connection.transaction()
        await transaction.start()
        university = await connection.fetchrow(
            """
            SELECT university_id
            FROM universities
            WHERE university_name ILIKE $1
            """,
            NORTHERN_NEW_MEXICO_COLLEGE_NAME,
        )
        if university is None:
            raise RuntimeError("Northern New Mexico College is missing from PostgreSQL")

        database_programs = await connection.fetch(
            """
            SELECT program_id, program_name, degree, total_credit_hours, metadata_json
            FROM programs
            WHERE university_id = $1
            """,
            university["university_id"],
        )
        all_program_ids = [program["program_id"] for program in database_programs]
        database_courses = await connection.fetch(
            """
            SELECT course_id, program_id, course_code, course_name, credits,
                   lecture_hours, lab_hours, recommended_year, recommended_semester,
                   description, metadata_json
            FROM courses
            WHERE program_id = ANY($1::uuid[])
            """,
            all_program_ids,
        )
        courses_by_program: dict[Any, list[asyncpg.Record]] = defaultdict(list)
        for database_course in database_courses:
            courses_by_program[database_course["program_id"]].append(database_course)

        programs_by_identity = {
            (program["program_name"], program["degree"]): program for program in database_programs
        }
        missing_programs = [
            program_identity(catalog_program)
            for catalog_program in snapshot["programs"]
            if program_identity(catalog_program) not in programs_by_identity
        ]
        if missing_programs:
            raise RuntimeError(
                "Catalog programs do not have stable database identities: "
                + ", ".join(f"{name} ({degree})" for name, degree in missing_programs)
            )

        program_rows: list[tuple[Any, int, str]] = []
        course_rows: list[tuple[Any, ...]] = []
        current_program_ids = set()

        def metadata(value: Any) -> dict[str, Any]:
            if isinstance(value, dict):
                return value
            return json.loads(value) if value else {}

        def course_row(
            course_id: Any,
            program_id: Any,
            course_code: str,
            course_name: str,
            credits: int,
            lecture_hours: int,
            lab_hours: int,
            recommended_year: int | None,
            recommended_semester: str | None,
            description: str | None,
            metadata_json: dict[str, Any],
            source_sequence: int | None,
        ) -> tuple[Any, ...]:
            return (
                course_id,
                program_id,
                course_code,
                course_name,
                credits,
                lecture_hours,
                lab_hours,
                recommended_year,
                recommended_semester,
                description,
                json.dumps(metadata_json, ensure_ascii=False),
                source_sequence,
            )

        for catalog_program in snapshot["programs"]:
            program = programs_by_identity[program_identity(catalog_program)]
            program_id = program["program_id"]
            current_program_ids.add(program_id)
            summary["programs_verified"] += 1
            program_rows.append(
                (
                    program_id,
                    int(catalog_program["totalCredits"]),
                    json.dumps(
                        _program_metadata(
                            metadata(program["metadata_json"]),
                            catalog_program,
                            snapshot,
                        ),
                        ensure_ascii=False,
                    ),
                )
            )

            existing_courses = courses_by_program[program_id]
            courses_by_code = {
                _canonical_code(course["course_code"]): course for course in existing_courses
            }
            current_course_ids = set()

            for coid, occurrences in aggregate_program_courses(catalog_program).items():
                detail = course_details[coid]
                code = str(detail["code"]).strip()
                course = courses_by_code.get(_canonical_code(code))
                recommended_year = _first_reported(occurrences, "recommendedYear")
                recommended_semester = _first_reported(occurrences, "recommendedSemester")
                existing_metadata = metadata(course["metadata_json"]) if course else {}
                course_rows.append(
                    course_row(
                        course["course_id"] if course else None,
                        program_id,
                        code,
                        str(detail["name"]).strip(),
                        int(detail["creditsMin"]),
                        _storage_hours(
                            detail.get("lectureHours"),
                            course["lecture_hours"] if course else None,
                        ),
                        _storage_hours(
                            detail.get("labHours"),
                            course["lab_hours"] if course else None,
                        ),
                        _recommended_year(
                            recommended_year,
                            existing_metadata,
                            course["recommended_year"] if course else None,
                        ),
                        _recommended_semester(
                            recommended_semester,
                            existing_metadata,
                            course["recommended_semester"] if course else None,
                        ),
                        (detail.get("fields") or {})["description"],
                        _course_metadata(
                            existing_metadata,
                            detail,
                            occurrences,
                            snapshot,
                        ),
                        min(occurrence.get("sequence") or 0 for occurrence in occurrences),
                    )
                )
                if course:
                    current_course_ids.add(course["course_id"])
                else:
                    summary["courses_added"] += 1
                summary["courses_verified"] += 1

            for course in existing_courses:
                if course["course_id"] in current_course_ids:
                    continue
                course_metadata = metadata(course["metadata_json"])
                if course_metadata.get("is_current_catalog") is not False:
                    summary["courses_marked_inactive"] += 1
                course_rows.append(
                    course_row(
                        course["course_id"],
                        course["program_id"],
                        course["course_code"],
                        course["course_name"],
                        course["credits"],
                        course["lecture_hours"],
                        course["lab_hours"],
                        course["recommended_year"],
                        course["recommended_semester"],
                        course["description"],
                        _merge_metadata(
                            course_metadata,
                            {
                                "is_current_catalog": False,
                                "retired_from_catalog_year": snapshot["catalogYear"],
                                "verified_on": VERIFIED_ON,
                            },
                        ),
                        None,
                    )
                )

        for program in database_programs:
            if program["program_id"] in current_program_ids:
                continue
            program_metadata = metadata(program["metadata_json"])
            if program_metadata.get("is_current_catalog") is not False:
                summary["programs_marked_inactive"] += 1
            program_rows.append(
                (
                    program["program_id"],
                    program["total_credit_hours"],
                    json.dumps(
                        _merge_metadata(
                            program_metadata,
                            {
                                "is_current_catalog": False,
                                "retired_from_catalog_year": snapshot["catalogYear"],
                                "verified_on": VERIFIED_ON,
                            },
                        ),
                        ensure_ascii=False,
                    ),
                )
            )
            for course in courses_by_program[program["program_id"]]:
                course_metadata = metadata(course["metadata_json"])
                if course_metadata.get("is_current_catalog") is not False:
                    summary["courses_marked_inactive"] += 1
                course_rows.append(
                    course_row(
                        course["course_id"],
                        course["program_id"],
                        course["course_code"],
                        course["course_name"],
                        course["credits"],
                        course["lecture_hours"],
                        course["lab_hours"],
                        course["recommended_year"],
                        course["recommended_semester"],
                        course["description"],
                        _merge_metadata(
                            course_metadata,
                            {
                                "is_current_catalog": False,
                                "retired_from_catalog_year": snapshot["catalogYear"],
                                "verified_on": VERIFIED_ON,
                            },
                        ),
                        None,
                    )
                )

        await connection.execute("""
            CREATE TEMP TABLE nnmc_program_sync (
                program_id uuid PRIMARY KEY,
                total_credit_hours integer NOT NULL,
                metadata_json text NOT NULL
            ) ON COMMIT DROP
            """)
        await connection.copy_records_to_table(
            "nnmc_program_sync",
            records=program_rows,
            columns=["program_id", "total_credit_hours", "metadata_json"],
        )
        await connection.execute("""
            CREATE TEMP TABLE nnmc_course_sync (
                course_id uuid,
                program_id uuid NOT NULL,
                course_code text NOT NULL,
                course_name text NOT NULL,
                credits integer NOT NULL,
                lecture_hours integer NOT NULL,
                lab_hours integer NOT NULL,
                recommended_year integer,
                recommended_semester text,
                description text,
                metadata_json text NOT NULL,
                source_sequence integer
            ) ON COMMIT DROP
            """)
        await connection.copy_records_to_table(
            "nnmc_course_sync",
            records=course_rows,
            columns=[
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
            ],
        )
        await connection.execute(
            """
            UPDATE courses
            SET source_sequence = NULL
            WHERE program_id = ANY($1::uuid[])
            """,
            all_program_ids,
        )
        await connection.execute("""
            UPDATE programs AS target
            SET total_credit_hours = source.total_credit_hours,
                metadata_json = source.metadata_json::jsonb
            FROM nnmc_program_sync AS source
            WHERE target.program_id = source.program_id
            """)
        await connection.execute("""
            UPDATE courses AS target
            SET program_id = source.program_id,
                course_code = source.course_code,
                course_name = source.course_name,
                credits = source.credits,
                lecture_hours = source.lecture_hours,
                lab_hours = source.lab_hours,
                recommended_year = source.recommended_year,
                recommended_semester = source.recommended_semester,
                description = source.description,
                metadata_json = source.metadata_json::jsonb,
                source_sequence = source.source_sequence
            FROM nnmc_course_sync AS source
            WHERE source.course_id IS NOT NULL
              AND target.course_id = source.course_id
            """)
        await connection.execute("""
            INSERT INTO courses (
                program_id, course_code, course_name, credits, lecture_hours,
                lab_hours, recommended_year, recommended_semester, description,
                metadata_json, source_sequence
            )
            SELECT program_id, course_code, course_name, credits, lecture_hours,
                   lab_hours, recommended_year, recommended_semester, description,
                   metadata_json::jsonb, source_sequence
            FROM nnmc_course_sync
            WHERE course_id IS NULL
            """)

        if apply_changes:
            await transaction.commit()
        else:
            await transaction.rollback()
    except Exception:
        try:
            await transaction.rollback()
        except asyncpg.InterfaceError:
            pass
        raise
    finally:
        await connection.close()

    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--snapshot",
        type=Path,
        default=DEFAULT_SNAPSHOT,
        help="Path to the authoritative browser-extracted NNMC catalog snapshot",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Commit the reconciliation. Without this flag the transaction is rolled back.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = load_snapshot(args.snapshot.resolve())
    summary = asyncio.run(reconcile(snapshot, apply_changes=args.apply))
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
