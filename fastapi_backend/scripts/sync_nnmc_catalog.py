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
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

import asyncpg  # type: ignore[import-untyped]
from sqlalchemy.engine import make_url

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.shared.catalog_requirements import (  # noqa: E402
    build_requirement_expressions,
    find_dangling_requirement_references,
    validate_catalog_reference_url,
)
from app.shared.constants.institution import (  # noqa: E402
    NORTHERN_NEW_MEXICO_COLLEGE_NAME,
)

DEFAULT_SNAPSHOT = BACKEND_ROOT / "data" / "nnmc_catalog_2025_2026.json"
EXPECTED_PROGRAMS = 66
EXPECTED_UNIQUE_COURSES = 515
EXPECTED_PROGRAM_ASSOCIATED_COURSES = 501
EXPECTED_PROGRAM_COURSE_OCCURRENCES = 1_439
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

# These identities exist only to find legacy database rows that predate official
# catalog source IDs. They must never be used as the desired persisted identity:
# the snapshot's official title and credential are authoritative.
LEGACY_PROGRAM_IDENTITIES = {
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

    duplicate_program_ids = sorted(
        program_id
        for program_id, count in Counter(
            str(program.get("poid") or "") for program in programs
        ).items()
        if count > 1
    )
    if duplicate_program_ids:
        errors.append(f"duplicate official program IDs: {duplicate_program_ids[:10]}")

    duplicate_course_ids = sorted(
        course_id
        for course_id, count in Counter(str(course.get("coid") or "") for course in courses).items()
        if count > 1
    )
    if duplicate_course_ids:
        errors.append(f"duplicate official course IDs: {duplicate_course_ids[:10]}")

    if snapshot.get("source") != "https://catalog.nnmc.edu/content.php?catoid=3&navoid=110":
        errors.append("catalog source must be the supplied NNMC catoid=3 program index")
    retrieved_at = snapshot.get("retrievedAt")
    try:
        datetime.fromisoformat(str(retrieved_at).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        errors.append("retrievedAt must be an ISO-8601 timestamp")

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

    associated_course_ids = {
        str(occurrence.get("coid") or "")
        for program in programs
        for occurrence in program.get("courses") or []
    }
    if len(associated_course_ids) != EXPECTED_PROGRAM_ASSOCIATED_COURSES:
        errors.append(
            "expected "
            f"{EXPECTED_PROGRAM_ASSOCIATED_COURSES} program-associated courses, "
            f"found {len(associated_course_ids)}"
        )

    for program in programs:
        parsed = urlparse(str(program.get("sourceUrl") or ""))
        query = parse_qs(parsed.query)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "catalog.nnmc.edu"
            or not parsed.path.endswith("preview_program.php")
            or query.get("catoid") != ["3"]
            or query.get("poid") != [str(program.get("poid"))]
        ):
            errors.append(f"invalid program source URL for poid={program.get('poid')}")
    for course in courses:
        if not validate_catalog_reference_url(
            str(course.get("sourceUrl") or ""),
            expected_id=str(course.get("coid") or ""),
        ):
            errors.append(f"invalid course source URL for coid={course.get('coid')}")

    dangling_references = find_dangling_requirement_references(snapshot)
    if dangling_references:
        errors.append(
            "dangling official requirement references: "
            + ", ".join(
                sorted({reference["referenced_course_id"] for reference in dangling_references})[
                    :10
                ]
            )
        )

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
    category = str(program["category"]).strip()
    if category == "Certificate":
        name = re.sub(r",?\s+Certificate$", "", title).strip()
        return name, category

    name = re.sub(r",\s*(?:BA|BS|BAIS|BBA|BEng|AA|AS|AAS|AEng)$", "", title).strip()
    return name, category


def legacy_program_identity(program: dict[str, Any]) -> tuple[str, str] | None:
    """Return a pre-source-ID lookup alias without changing official values."""
    return LEGACY_PROGRAM_IDENTITIES.get(str(program["title"]).strip())


def program_credit_range(program: dict[str, Any]) -> tuple[float, float]:
    """Return the official minimum and maximum credits reported in the title block."""
    reported = str(program.get("totalCreditsText") or "")
    values = [float(value) for value in re.findall(r"\d+(?:\.\d+)?", reported)]
    minimum = float(program["totalCredits"])
    if not values:
        return minimum, minimum
    return values[0], values[-1]


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


def _decimal_value(value: Any, *, default: str = "0") -> Decimal:
    """Normalize a source number without truncating fractional catalog values."""
    if value is None or value == "":
        return Decimal(default)
    return Decimal(str(value))


def _storage_hours(value: Any, _existing_value: Any = None) -> Decimal:
    """Return the exact catalog contact-hour value, defaulting only when absent."""
    return _decimal_value(value)


def _merge_metadata(existing: dict[str, Any] | None, updates: dict[str, Any]) -> dict:
    return {**(existing or {}), **updates}


def _program_metadata(
    existing: dict[str, Any] | None,
    program: dict[str, Any],
    snapshot: dict[str, Any],
) -> dict:
    credits_min, credits_max = program_credit_range(program)
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
            "catalog_total_credits_min": credits_min,
            "catalog_total_credits_max": credits_max,
            "catalog_source": snapshot["source"],
            "source_retrieved_at": snapshot["retrievedAt"],
            "verified_on": str(snapshot["retrievedAt"])[:10],
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
            "pre_or_corequisite": fields.get("prerequisites_or_corequisites"),
            "cross_listed_as": fields.get("cross_listed_as"),
            "requirement_expressions": build_requirement_expressions(detail),
            "requirement_occurrences": normalized_occurrences,
            "is_elective": is_elective,
            "source_retrieved_at": snapshot["retrievedAt"],
            "verified_on": str(snapshot["retrievedAt"])[:10],
        },
    )


PROGRAM_METADATA_KEYS = {
    "is_current_catalog",
    "catalog_year",
    "catalog_title",
    "catalog_url",
    "catalog_program_id",
    "catalog_category",
    "catalog_intro",
    "catalog_headings",
    "catalog_requirement_groups",
    "catalog_total_credits_text",
    "catalog_total_credits_min",
    "catalog_total_credits_max",
    "catalog_source",
    "source_retrieved_at",
    "verified_on",
}
COURSE_METADATA_KEYS = {
    "is_current_catalog",
    "catalog_year",
    "catalog_course_id",
    "catalog_course_title",
    "catalog_url",
    "catalog_source",
    "catalog_credit_text",
    "credit_contact_text",
    "credits_min",
    "credits_max",
    "lecture_hours_exact",
    "lab_hours_exact",
    "fields",
    "field_links",
    "prerequisite",
    "corequisite",
    "prerequisites_or_corequisites",
    "pre_or_corequisite",
    "cross_listed_as",
    "requirement_expressions",
    "requirement_occurrences",
    "is_elective",
    "source_retrieved_at",
    "verified_on",
}


def _metadata(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return json.loads(value) if value else {}


def _json_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, Decimal):
        return float(value)
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _record_changes(
    *,
    entity: str,
    identifier: str,
    action: str,
    local: dict[str, Any] | None,
    expected: dict[str, Any],
    scalar_fields: list[str],
    metadata_keys: set[str],
    source_url: str,
) -> dict[str, Any] | None:
    changes: list[dict[str, Any]] = []
    if local is None:
        changes.append(
            {
                "field": "record",
                "local_value": None,
                "official_value": {
                    field: _json_value(expected.get(field)) for field in scalar_fields
                },
                "difference_type": "missing_record",
                "proposed_correction": "Insert the verified catoid=3 record.",
            }
        )
    else:
        for field in scalar_fields:
            if local.get(field) != expected.get(field):
                changes.append(
                    {
                        "field": field,
                        "local_value": _json_value(local.get(field)),
                        "official_value": _json_value(expected.get(field)),
                        "difference_type": (
                            "extra_active_record" if action == "deactivate" else "value_mismatch"
                        ),
                        "proposed_correction": (
                            "Mark inactive without deleting history."
                            if action == "deactivate"
                            else "Set to the verified catoid=3 value."
                        ),
                    }
                )
        local_metadata = _metadata(local.get("metadata_json"))
        expected_metadata = _metadata(expected.get("metadata_json"))
        for key in sorted(metadata_keys):
            if local_metadata.get(key) != expected_metadata.get(key):
                changes.append(
                    {
                        "field": f"metadata_json.{key}",
                        "local_value": _json_value(local_metadata.get(key)),
                        "official_value": _json_value(expected_metadata.get(key)),
                        "difference_type": (
                            "extra_active_record" if action == "deactivate" else "value_mismatch"
                        ),
                        "proposed_correction": (
                            "Mark inactive without deleting history."
                            if action == "deactivate"
                            else "Set to the verified catoid=3 value."
                        ),
                    }
                )

    if not changes:
        return None
    return {
        "entity": entity,
        "identifier": identifier,
        "action": action,
        "official_source_url": source_url,
        "changes": changes,
    }


async def _table_columns(connection: asyncpg.Connection, table_name: str) -> set[str]:
    records = await connection.fetch(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = $1
        """,
        table_name,
    )
    return {record["column_name"] for record in records}


async def _upsert_rows(
    connection: asyncpg.Connection,
    table_name: str,
    primary_key: str,
    columns: list[str],
    rows: list[dict[str, Any]],
) -> None:
    if not rows:
        return
    placeholders = ", ".join(f"${index}" for index in range(1, len(columns) + 1))
    assignments = ", ".join(
        f"{column} = EXCLUDED.{column}" for column in columns if column != primary_key
    )
    statement = (
        f"INSERT INTO {table_name} ({', '.join(columns)}) VALUES ({placeholders}) "
        f"ON CONFLICT ({primary_key}) DO UPDATE SET {assignments}"
    )
    values = [
        tuple(
            (
                json.dumps(row[column], ensure_ascii=False)
                if column == "metadata_json"
                else row[column]
            )
            for column in columns
        )
        for row in rows
    ]
    if "metadata_json" in columns:
        metadata_position = columns.index("metadata_json") + 1
        statement = statement.replace(
            f"${metadata_position}",
            f"${metadata_position}::jsonb",
            1,
        )
    await connection.executemany(statement, values)


async def reconcile(
    snapshot: dict[str, Any],
    *,
    apply_changes: bool,
    simulate_failure: bool = False,
) -> dict[str, Any]:
    if apply_changes and settings.environment != "development":
        raise RuntimeError(
            "Catalog synchronization writes are restricted to ENVIRONMENT=development."
        )
    if simulate_failure and not apply_changes:
        raise ValueError("simulate_failure requires apply_changes=True")

    course_details = {str(course["coid"]): course for course in snapshot["courses"]}
    retrieved_at = datetime.fromisoformat(str(snapshot["retrievedAt"]).replace("Z", "+00:00"))
    database_url = make_url(settings.database_url)
    dsn = database_url.set(drivername="postgresql").render_as_string(hide_password=False)
    connection = await asyncpg.connect(dsn)
    transaction = connection.transaction()
    await transaction.start()

    try:
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

        program_columns = await _table_columns(connection, "programs")
        course_columns = await _table_columns(connection, "courses")
        source_columns = [
            column
            for column in ("official_source_id", "official_source_url", "source_retrieved_at")
            if column in program_columns
        ]
        course_source_columns = [
            column
            for column in ("official_source_id", "official_source_url", "source_retrieved_at")
            if column in course_columns
        ]
        program_select_columns = [
            "program_id",
            "university_id",
            "program_name",
            "degree",
            "total_credit_hours",
            "metadata_json",
            *source_columns,
        ]
        course_select_columns = [
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
            *course_source_columns,
        ]
        database_program_records = await connection.fetch(
            f"SELECT {', '.join(program_select_columns)} FROM programs WHERE university_id = $1",
            university["university_id"],
        )
        database_programs = [dict(record) for record in database_program_records]
        existing_program_ids = [program["program_id"] for program in database_programs]
        database_course_records = (
            await connection.fetch(
                f"SELECT {', '.join(course_select_columns)} FROM courses "
                "WHERE program_id = ANY($1::uuid[])",
                existing_program_ids,
            )
            if existing_program_ids
            else []
        )
        database_courses = [dict(record) for record in database_course_records]
        courses_by_program: dict[Any, list[dict[str, Any]]] = defaultdict(list)
        for database_course in database_courses:
            courses_by_program[database_course["program_id"]].append(database_course)

        programs_by_identity = {
            (program["program_name"], program["degree"]): program for program in database_programs
        }
        programs_by_official_id: dict[str, dict[str, Any]] = {}
        for program in database_programs:
            metadata = _metadata(program.get("metadata_json"))
            official_id = program.get("official_source_id") or metadata.get("catalog_program_id")
            if official_id:
                programs_by_official_id[str(official_id)] = program

        expected_program_rows: list[dict[str, Any]] = []
        expected_course_rows: list[dict[str, Any]] = []
        changes: list[dict[str, Any]] = []
        current_program_ids: set[Any] = set()
        current_course_ids: set[Any] = set()
        program_stats = {"inserted": 0, "updated": 0, "deactivated": 0, "unchanged": 0}
        course_stats = {"inserted": 0, "updated": 0, "deactivated": 0, "unchanged": 0}

        program_scalar_fields = [
            "program_name",
            "degree",
            "total_credit_hours",
            *source_columns,
        ]
        course_scalar_fields = [
            "course_code",
            "course_name",
            "credits",
            "lecture_hours",
            "lab_hours",
            "recommended_year",
            "recommended_semester",
            "description",
            "source_sequence",
            *course_source_columns,
        ]

        for catalog_program in snapshot["programs"]:
            official_program_id = str(catalog_program["poid"])
            identity = program_identity(catalog_program)
            legacy_identity = legacy_program_identity(catalog_program)
            existing_program = (
                programs_by_official_id.get(official_program_id)
                or programs_by_identity.get(identity)
                or (programs_by_identity.get(legacy_identity) if legacy_identity else None)
            )
            program_id = existing_program["program_id"] if existing_program else uuid.uuid4()
            current_program_ids.add(program_id)
            program_metadata = _program_metadata(
                _metadata(existing_program.get("metadata_json")) if existing_program else {},
                catalog_program,
                snapshot,
            )
            expected_program: dict[str, Any] = {
                "program_id": program_id,
                "university_id": university["university_id"],
                "program_name": identity[0],
                "degree": identity[1],
                "total_credit_hours": int(catalog_program["totalCredits"]),
                "metadata_json": program_metadata,
            }
            if "official_source_id" in source_columns:
                expected_program["official_source_id"] = official_program_id
            if "official_source_url" in source_columns:
                expected_program["official_source_url"] = catalog_program["sourceUrl"]
            if "source_retrieved_at" in source_columns:
                expected_program["source_retrieved_at"] = retrieved_at
            program_change = _record_changes(
                entity="program",
                identifier=official_program_id,
                action="insert" if existing_program is None else "update",
                local=existing_program,
                expected=expected_program,
                scalar_fields=program_scalar_fields,
                metadata_keys=PROGRAM_METADATA_KEYS,
                source_url=catalog_program["sourceUrl"],
            )
            if program_change:
                action = "inserted" if existing_program is None else "updated"
                program_stats[action] += 1
                expected_program_rows.append(expected_program)
                changes.append(program_change)
            else:
                program_stats["unchanged"] += 1

            existing_courses = courses_by_program[program_id]
            courses_by_code = {
                _canonical_code(course["course_code"]): course for course in existing_courses
            }
            courses_by_official_id: dict[str, dict[str, Any]] = {}
            for existing_course in existing_courses:
                metadata = _metadata(existing_course.get("metadata_json"))
                official_id = existing_course.get("official_source_id") or metadata.get(
                    "catalog_course_id"
                )
                if official_id:
                    courses_by_official_id[str(official_id)] = existing_course

            for coid, occurrences in aggregate_program_courses(catalog_program).items():
                detail = course_details[coid]
                code = str(detail["code"]).strip()
                matched_course = courses_by_official_id.get(coid) or courses_by_code.get(
                    _canonical_code(code)
                )
                course_id = matched_course["course_id"] if matched_course else uuid.uuid4()
                current_course_ids.add(course_id)
                existing_metadata = (
                    _metadata(matched_course.get("metadata_json")) if matched_course else {}
                )
                recommended_year = _first_reported(occurrences, "recommendedYear")
                recommended_semester = _first_reported(occurrences, "recommendedSemester")
                expected_course: dict[str, Any] = {
                    "course_id": course_id,
                    "program_id": program_id,
                    "course_code": code,
                    "course_name": str(detail["name"]).strip(),
                    "credits": _decimal_value(detail["creditsMin"], default="1"),
                    "lecture_hours": _storage_hours(
                        detail.get("lectureHours"),
                        matched_course.get("lecture_hours") if matched_course else None,
                    ),
                    "lab_hours": _storage_hours(
                        detail.get("labHours"),
                        matched_course.get("lab_hours") if matched_course else None,
                    ),
                    "recommended_year": _recommended_year(
                        recommended_year,
                        existing_metadata,
                        matched_course.get("recommended_year") if matched_course else None,
                    ),
                    "recommended_semester": _recommended_semester(
                        recommended_semester,
                        existing_metadata,
                        matched_course.get("recommended_semester") if matched_course else None,
                    ),
                    "description": (detail.get("fields") or {}).get("description"),
                    "metadata_json": _course_metadata(
                        existing_metadata,
                        detail,
                        occurrences,
                        snapshot,
                    ),
                    "source_sequence": min(
                        occurrence.get("sequence") or 0 for occurrence in occurrences
                    ),
                }
                if "official_source_id" in course_source_columns:
                    expected_course["official_source_id"] = coid
                if "official_source_url" in course_source_columns:
                    expected_course["official_source_url"] = detail["sourceUrl"]
                if "source_retrieved_at" in course_source_columns:
                    expected_course["source_retrieved_at"] = retrieved_at
                course_change = _record_changes(
                    entity="course",
                    identifier=f"{official_program_id}:{coid}",
                    action="insert" if matched_course is None else "update",
                    local=matched_course,
                    expected=expected_course,
                    scalar_fields=course_scalar_fields,
                    metadata_keys=COURSE_METADATA_KEYS,
                    source_url=detail["sourceUrl"],
                )
                if course_change:
                    action = "inserted" if matched_course is None else "updated"
                    course_stats[action] += 1
                    expected_course_rows.append(expected_course)
                    changes.append(course_change)
                else:
                    course_stats["unchanged"] += 1

        for program in database_programs:
            if program["program_id"] in current_program_ids:
                continue
            metadata = _metadata(program.get("metadata_json"))
            if metadata.get("is_current_catalog") is False:
                continue
            expected_program = {
                **program,
                "metadata_json": _merge_metadata(
                    metadata,
                    {
                        "is_current_catalog": False,
                        "retired_from_catalog_year": snapshot["catalogYear"],
                        "verified_on": str(snapshot["retrievedAt"])[:10],
                    },
                ),
            }
            program_change = _record_changes(
                entity="program",
                identifier=str(
                    program.get("official_source_id")
                    or metadata.get("catalog_program_id")
                    or program["program_id"]
                ),
                action="deactivate",
                local=program,
                expected=expected_program,
                scalar_fields=program_scalar_fields,
                metadata_keys={"is_current_catalog", "retired_from_catalog_year", "verified_on"},
                source_url=snapshot["source"],
            )
            if program_change:
                program_stats["deactivated"] += 1
                expected_program_rows.append(expected_program)
                changes.append(program_change)

        for course in database_courses:
            if course["course_id"] in current_course_ids:
                continue
            metadata = _metadata(course.get("metadata_json"))
            if metadata.get("is_current_catalog") is False:
                continue
            expected_course = {
                **course,
                "source_sequence": None,
                "metadata_json": _merge_metadata(
                    metadata,
                    {
                        "is_current_catalog": False,
                        "retired_from_catalog_year": snapshot["catalogYear"],
                        "verified_on": str(snapshot["retrievedAt"])[:10],
                    },
                ),
            }
            course_change = _record_changes(
                entity="course",
                identifier=str(
                    course.get("official_source_id")
                    or metadata.get("catalog_course_id")
                    or course["course_id"]
                ),
                action="deactivate",
                local=course,
                expected=expected_course,
                scalar_fields=course_scalar_fields,
                metadata_keys={"is_current_catalog", "retired_from_catalog_year", "verified_on"},
                source_url=snapshot["source"],
            )
            if course_change:
                course_stats["deactivated"] += 1
                expected_course_rows.append(expected_course)
                changes.append(course_change)

        if apply_changes:
            await _upsert_rows(
                connection,
                "programs",
                "program_id",
                [
                    "program_id",
                    "university_id",
                    "program_name",
                    "degree",
                    "total_credit_hours",
                    "metadata_json",
                    *source_columns,
                ],
                expected_program_rows,
            )
            await _upsert_rows(
                connection,
                "courses",
                "course_id",
                course_select_columns,
                expected_course_rows,
            )
            if simulate_failure:
                raise RuntimeError("Simulated catalog synchronization failure")
            await transaction.commit()
        else:
            await transaction.rollback()

        active_course_rows_after = sum(
            len(aggregate_program_courses(program)) for program in snapshot["programs"]
        )
        return {
            "mode": "apply" if apply_changes else "dry-run",
            "catalog": {
                "source": snapshot["source"],
                "catalog_year": snapshot["catalogYear"],
                "retrieved_at": snapshot["retrievedAt"],
                "programs": len(snapshot["programs"]),
                "course_details": len(snapshot["courses"]),
                "program_associated_course_details": EXPECTED_PROGRAM_ASSOCIATED_COURSES,
                "program_course_occurrences": EXPECTED_PROGRAM_COURSE_OCCURRENCES,
                "active_program_course_rows": active_course_rows_after,
            },
            "database_before": {
                "program_rows": len(database_programs),
                "active_program_rows": sum(
                    _metadata(program.get("metadata_json")).get("is_current_catalog") is not False
                    for program in database_programs
                ),
                "course_rows": len(database_courses),
                "active_course_rows": sum(
                    _metadata(course.get("metadata_json")).get("is_current_catalog") is not False
                    for course in database_courses
                ),
                "program_source_columns": source_columns,
                "course_source_columns": course_source_columns,
            },
            "database_after_expected": {
                "active_program_rows": len(snapshot["programs"]),
                "active_course_rows": active_course_rows_after,
            },
            "programs": program_stats,
            "courses": course_stats,
            "pending_change_count": len(changes),
            "changes": sorted(
                changes,
                key=lambda change: (
                    change["entity"],
                    change["action"],
                    change["identifier"],
                ),
            ),
        }
    except Exception:
        try:
            await transaction.rollback()
        except asyncpg.InterfaceError:
            pass
        raise
    finally:
        await connection.close()


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
    parser.add_argument(
        "--simulate-failure",
        action="store_true",
        help="Write inside the transaction, then raise before commit to verify rollback.",
    )
    parser.add_argument(
        "--diff-output",
        type=Path,
        help="Write the complete field-level diff as JSON while printing only a compact summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    snapshot = load_snapshot(args.snapshot.resolve())
    summary = asyncio.run(
        reconcile(
            snapshot,
            apply_changes=args.apply,
            simulate_failure=args.simulate_failure,
        )
    )
    if args.diff_output:
        output_path = args.diff_output.resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            f"{json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True)}\n",
            encoding="utf-8",
        )
        compact = {key: value for key, value in summary.items() if key != "changes"}
        compact["diff_output"] = str(output_path)
        print(json.dumps(compact, indent=2, sort_keys=True))
    else:
        print(json.dumps(summary, indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
