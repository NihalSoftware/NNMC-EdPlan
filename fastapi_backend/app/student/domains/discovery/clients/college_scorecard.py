from __future__ import annotations

import asyncio
import re
from collections.abc import Mapping
from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.shared.constants.institution import (
    NORTHERN_NEW_MEXICO_COLLEGE_SCORECARD_ID,
    is_northern_new_mexico_college,
)

BASE_FIELDS = [
    "id",
    "school.name",
    "school.city",
    "school.state",
    "school.school_url",
    "school.ownership",
    "school.locale",
    "school.accreditor",
    "school.open_admissions_policy",
    "school.degrees_awarded.predominant",
    "school.degrees_awarded.highest",
    "school.main_campus",
    "school.branches",
    "latest.student.size",
    "latest.student.part_time_share",
    "latest.completion.consumer_rate",
    "latest.cost.avg_net_price.overall",
    "latest.cost.tuition.in_state",
    "latest.cost.tuition.out_of_state",
    "latest.cost.roomboard.oncampus",
    "latest.cost.booksupply",
    "latest.earnings.10_yrs_after_entry.median",
    "latest.aid.median_debt.completers.overall",
    "latest.aid.median_debt.completers.monthly_payments",
    "latest.student.share_white",
    "latest.student.share_black",
    "latest.student.share_hispanic",
    "latest.student.share_asian",
    "latest.student.share_two_or_more",
    "latest.student.share_non_resident_alien",
    "latest.student.share_firstgeneration",
    "latest.student.demographics.race_ethnicity.white",
    "latest.student.demographics.race_ethnicity.black",
    "latest.student.demographics.race_ethnicity.hispanic",
    "latest.student.demographics.race_ethnicity.asian",
    "latest.student.demographics.race_ethnicity.two_or_more",
    "latest.student.demographics.race_ethnicity.non_resident_alien",
    "latest.student.demographics.first_generation",
    "latest.aid.pell_grant_rate",
    "latest.aid.dcs_federal_loan_rate_pooled",
    "latest.student.demographics.student_faculty_ratio",
    "latest.student.retention_rate_suppressed.four_year.full_time_pooled",
    "latest.student.retention_rate_suppressed.lt_four_year.full_time_pooled",
    "latest.admissions.sat_scores.25th_percentile.critical_reading",
    "latest.admissions.sat_scores.75th_percentile.critical_reading",
    "latest.admissions.act_scores.25th_percentile.cumulative",
    "latest.admissions.act_scores.75th_percentile.cumulative",
    "latest.admissions.admission_rate.overall",
    "latest.repayment.3_yr_repayment.completers.rate",
    "latest.earnings.6_yrs_after_entry.gt_threshold",
    "latest.cost.net_price.public.by_income_level.0-30000",
    "latest.cost.net_price.public.by_income_level.30001-48000",
    "latest.cost.net_price.public.by_income_level.48001-75000",
    "latest.cost.net_price.public.by_income_level.75001-110000",
    "latest.cost.net_price.public.by_income_level.110001-plus",
    "latest.cost.net_price.private.by_income_level.0-30000",
    "latest.cost.net_price.private.by_income_level.30001-48000",
    "latest.cost.net_price.private.by_income_level.48001-75000",
    "latest.cost.net_price.private.by_income_level.75001-110000",
    "latest.cost.net_price.private.by_income_level.110001-plus",
]

OWNERSHIP_MAP = {1: "Public", 2: "Private nonprofit", 3: "Private for-profit"}

HIGHEST_DEGREE_MAP = {
    0: "Non-degree-granting",
    1: "Certificate",
    2: "Associate degree",
    3: "Bachelor's degree",
    4: "Graduate degree",
}

PREDOMINANT_DEGREE_MAP = {
    0: "Not classified",
    1: "Predominantly certificate",
    2: "Predominantly associate degree",
    3: "Predominantly bachelor's degree",
    4: "Entirely graduate degree",
}

LOCALE_MAP = {
    11: "City",
    12: "City",
    13: "City",
    21: "Suburban",
    22: "Suburban",
    23: "Suburban",
    31: "Town",
    32: "Town",
    33: "Town",
    41: "Rural",
    42: "Rural",
    43: "Rural",
}

STATE_ABBREVIATIONS = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "district of columbia": "DC",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}


class CollegeScorecardClient:
    def __init__(self) -> None:
        self.base_url = settings.college_scorecard_base_url.rstrip("/")
        self.api_key = settings.college_scorecard_api_key
        self._profile_cache: dict[tuple[str, str, str], dict[str, Any] | None] = {}

    @retry(
        retry=retry_if_exception(
            lambda exc: isinstance(exc, httpx.RequestError)
            or (
                isinstance(exc, httpx.HTTPStatusError)
                and (exc.response.status_code == 429 or exc.response.status_code >= 500)
            )
        ),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
        reraise=True,
    )
    async def _get(
        self,
        path: str,
        params: Mapping[str, str | int | float | bool | None],
    ) -> dict[str, Any]:
        query: dict[str, str | int | float | bool | None] = {
            "api_key": self.api_key,
            "per_page": 25,
        }
        query.update(params)
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.get(f"{self.base_url}{path}", params=query)
            response.raise_for_status()
            return response.json()

    async def search_schools(
        self,
        *,
        search: str | None = None,
        state: str | None = None,
        page: int = 0,
        per_page: int = 25,
    ) -> dict[str, Any]:
        params: dict[str, str | int | float | bool | None] = {
            "id": NORTHERN_NEW_MEXICO_COLLEGE_SCORECARD_ID,
            "page": 0,
            "per_page": 1,
            "fields": ",".join(BASE_FIELDS),
            "sort": "latest.student.size:desc",
        }
        payload = await self._get("/schools", params)
        schools = [self._map_school(result) for result in payload.get("results", [])]
        return {"results": schools, "metadata": payload.get("metadata", {})}

    async def get_school(self, unit_id: str) -> dict[str, Any] | None:
        if str(unit_id) != NORTHERN_NEW_MEXICO_COLLEGE_SCORECARD_ID:
            return None
        params: dict[str, str | int | float | bool | None] = {
            "id": NORTHERN_NEW_MEXICO_COLLEGE_SCORECARD_ID,
            "fields": ",".join(BASE_FIELDS),
        }
        payload = await self._get("/schools", params)
        if not payload.get("results"):
            return None
        return self._map_school(payload["results"][0])

    async def find_schools_by_profiles(
        self,
        profiles: list[dict[str, Any]],
    ) -> list[dict[str, Any] | None]:
        if not profiles:
            return []

        matches: list[dict[str, Any] | None] = [None] * len(profiles)
        uncached_by_state: dict[str, list[int]] = {}

        for index, profile in enumerate(profiles):
            cache_key = _profile_cache_key(
                profile.get("name") or profile.get("university_name") or "",
                profile.get("city"),
                profile.get("state"),
            )
            if cache_key in self._profile_cache:
                matches[index] = self._profile_cache[cache_key]
                continue
            if cache_key[2]:
                uncached_by_state.setdefault(cache_key[2], []).append(index)

        state_codes = list(uncached_by_state)
        state_payloads = await asyncio.gather(
            *(self.search_schools(state=state_code, per_page=100) for state_code in state_codes),
            return_exceptions=True,
        )
        candidates_by_state = {
            state_code: (payload.get("results", []) if isinstance(payload, dict) else [])
            for state_code, payload in zip(state_codes, state_payloads, strict=True)
        }

        fallback_indices: list[int] = []
        for index, profile in enumerate(profiles):
            cache_key = _profile_cache_key(
                profile.get("name") or profile.get("university_name") or "",
                profile.get("city"),
                profile.get("state"),
            )
            if cache_key in self._profile_cache:
                matches[index] = self._profile_cache[cache_key]
                continue

            candidate = _match_mapped_school(
                profile,
                candidates_by_state.get(cache_key[2], []),
            )
            if candidate is not None:
                matches[index] = candidate
                self._cache_profile(cache_key, candidate)
            else:
                fallback_indices.append(index)

        fallback_matches = await asyncio.gather(
            *(
                self.find_school_by_profile(
                    name=profiles[index].get("name")
                    or profiles[index].get("university_name")
                    or "",
                    city=profiles[index].get("city"),
                    state=profiles[index].get("state"),
                )
                for index in fallback_indices
            )
        )
        for index, match in zip(fallback_indices, fallback_matches, strict=True):
            matches[index] = match

        return matches

    async def find_school_by_profile(
        self,
        *,
        name: str,
        city: str | None = None,
        state: str | None = None,
    ) -> dict[str, Any] | None:
        if not is_northern_new_mexico_college(name):
            return None

        return await self.get_school(NORTHERN_NEW_MEXICO_COLLEGE_SCORECARD_ID)

    def _cache_profile(
        self,
        key: tuple[str, str, str],
        school: dict[str, Any] | None,
    ) -> None:
        if len(self._profile_cache) >= 500:
            self._profile_cache.pop(next(iter(self._profile_cache)))
        self._profile_cache[key] = school

    def _map_school(self, record: dict[str, Any]) -> dict[str, Any]:
        ownership_code = _optional_int(record.get("school.ownership"))
        locale_code = _optional_int(record.get("school.locale"))
        predominant_degree_code = _optional_int(record.get("school.degrees_awarded.predominant"))
        highest_degree_code = _optional_int(record.get("school.degrees_awarded.highest"))
        graduation_rate = record.get("latest.completion.consumer_rate")
        avg_cost = record.get("latest.cost.avg_net_price.overall")
        median_earnings = record.get("latest.earnings.10_yrs_after_entry.median")
        sat_reading_25th = record.get(
            "latest.admissions.sat_scores.25th_percentile.critical_reading"
        )
        sat_reading_75th = record.get(
            "latest.admissions.sat_scores.75th_percentile.critical_reading"
        )
        act_score_25th = record.get("latest.admissions.act_scores.25th_percentile.cumulative")
        act_score_75th = record.get("latest.admissions.act_scores.75th_percentile.cumulative")
        acceptance_rate = record.get("latest.admissions.admission_rate.overall")
        open_admissions = record.get("school.open_admissions_policy")
        part_time_share = record.get("latest.student.part_time_share")
        size = record.get("latest.student.size") or 0
        full_time_enrollment = None
        part_time_enrollment = None
        if size and part_time_share is not None:
            full_time_enrollment = int(round(size * (1 - part_time_share)))
            part_time_enrollment = int(round(size * part_time_share))
        student_faculty_ratio = record.get("latest.student.demographics.student_faculty_ratio")
        non_resident_share = _first_non_null(
            record,
            "latest.student.share_non_resident_alien",
            "latest.student.demographics.race_ethnicity.non_resident_alien",
        )
        international_students = None
        if size and non_resident_share is not None:
            international_students = int(round(size * non_resident_share))
        diversity = {
            "white": _first_non_null(
                record,
                "latest.student.share_white",
                "latest.student.demographics.race_ethnicity.white",
            ),
            "black": _first_non_null(
                record,
                "latest.student.share_black",
                "latest.student.demographics.race_ethnicity.black",
            ),
            "hispanic": _first_non_null(
                record,
                "latest.student.share_hispanic",
                "latest.student.demographics.race_ethnicity.hispanic",
            ),
            "asian": _first_non_null(
                record,
                "latest.student.share_asian",
                "latest.student.demographics.race_ethnicity.asian",
            ),
            "two_or_more": _first_non_null(
                record,
                "latest.student.share_two_or_more",
                "latest.student.demographics.race_ethnicity.two_or_more",
            ),
            "non_resident": non_resident_share,
        }
        monthly_payment_median = record.get("latest.aid.median_debt.completers.monthly_payments")
        typical_monthly_payment = monthly_payment_median

        income_levels = [
            "0-30000",
            "30001-48000",
            "48001-75000",
            "75001-110000",
            "110001-plus",
        ]

        def _income_breakdown(prefix: str) -> dict[str, Any]:
            return {
                level: record.get(f"latest.cost.net_price.{prefix}.by_income_level.{level}")
                for level in income_levels
            }

        def _clean_breakdown(data: dict[str, Any]) -> dict[str, Any]:
            return {level: value for level, value in data.items() if value is not None}

        public_net_price = _clean_breakdown(_income_breakdown("public"))
        private_net_price = _clean_breakdown(_income_breakdown("private"))

        family_income_net_price = None
        if public_net_price:
            family_income_net_price = {"source": "public", "breakdown": public_net_price}
        elif private_net_price:
            family_income_net_price = {"source": "private", "breakdown": private_net_price}

        retention_candidates = [
            record.get("latest.student.retention_rate_suppressed.four_year.full_time_pooled"),
            record.get("latest.student.retention_rate_suppressed.lt_four_year.full_time_pooled"),
        ]
        first_year_retention = next(
            (value for value in retention_candidates if value is not None), None
        )

        scorecard_unit_id = record.get("id")
        school_name = record.get("school.name")
        school_city = record.get("school.city")
        school_state = record.get("school.state")
        school_url = record.get("school.school_url")

        return {
            "unit_id": scorecard_unit_id,
            "scorecard_unit_id": scorecard_unit_id,
            "scorecard_source_url": (
                f"https://collegescorecard.ed.gov/school/?{scorecard_unit_id}"
                if scorecard_unit_id
                else None
            ),
            "name": school_name,
            "city": school_city,
            "state": school_state,
            "website": school_url,
            "organization_type": (
                OWNERSHIP_MAP.get(ownership_code, "Other")
                if ownership_code is not None
                else "Other"
            ),
            "size": record.get("latest.student.size"),
            "location_type": (
                LOCALE_MAP.get(locale_code, "Other") if locale_code is not None else "Other"
            ),
            "accreditor": record.get("school.accreditor"),
            "open_admissions_policy": (open_admissions == 1 if open_admissions in (1, 2) else None),
            "predominant_degree": (
                PREDOMINANT_DEGREE_MAP.get(predominant_degree_code)
                if predominant_degree_code is not None
                else None
            ),
            "highest_degree": (
                HIGHEST_DEGREE_MAP.get(highest_degree_code)
                if highest_degree_code is not None
                else None
            ),
            "main_campus": (
                bool(record.get("school.main_campus"))
                if record.get("school.main_campus") is not None
                else None
            ),
            "branch_count": record.get("school.branches"),
            "graduation_rate": graduation_rate,
            "average_annual_cost": avg_cost,
            "in_state_tuition": record.get("latest.cost.tuition.in_state"),
            "out_of_state_tuition": record.get("latest.cost.tuition.out_of_state"),
            "on_campus_room_and_board": record.get("latest.cost.roomboard.oncampus"),
            "books_and_supplies": record.get("latest.cost.booksupply"),
            "median_earnings": median_earnings,
            "financial_aid_debt": record.get("latest.aid.median_debt.completers.overall"),
            "typical_earnings": median_earnings,
            "campus_diversity": diversity,
            "sat_reading_25th": sat_reading_25th,
            "sat_reading_75th": sat_reading_75th,
            "act_score_25th": act_score_25th,
            "act_score_75th": act_score_75th,
            "acceptance_rate": acceptance_rate,
            "full_time_enrollment": full_time_enrollment,
            "part_time_enrollment": part_time_enrollment,
            "international_students": international_students,
            "first_year_return_rate": first_year_retention,
            "student_faculty_ratio": student_faculty_ratio,
            "federal_loan_rate": record.get("latest.aid.dcs_federal_loan_rate_pooled"),
            "median_debt": record.get("latest.aid.median_debt.completers.overall"),
            "typical_monthly_payment": typical_monthly_payment,
            "repayment_rate": record.get("latest.repayment.3_yr_repayment.completers.rate"),
            "percent_more_than_hs": record.get("latest.earnings.6_yrs_after_entry.gt_threshold"),
            "family_income_net_price": family_income_net_price,
            "socioeconomic_diversity": {
                "first_generation_share": _first_non_null(
                    record,
                    "latest.student.share_firstgeneration",
                    "latest.student.demographics.first_generation",
                ),
                "pell_grant_rate": record.get("latest.aid.pell_grant_rate"),
            },
            "college_info": {
                "type": (
                    OWNERSHIP_MAP.get(ownership_code, "Other")
                    if ownership_code is not None
                    else "Other"
                ),
                "setting": (
                    LOCALE_MAP.get(locale_code, "Other") if locale_code is not None else "Other"
                ),
                "website": school_url,
                "location": ", ".join(filter(None, [school_city, school_state])),
            },
        }


def _first_non_null(record: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        value = record.get(key)
        if value is not None:
            return value
    return None


def _optional_int(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _state_code(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = value.strip()
    if len(cleaned) == 2:
        return cleaned.upper()
    return STATE_ABBREVIATIONS.get(cleaned.lower())


def _profile_cache_key(
    name: str,
    city: str | None,
    state: str | None,
) -> tuple[str, str, str]:
    return (
        _normalize_school_name(name),
        _normalize_simple(city),
        _state_code(state) or "",
    )


def _match_mapped_school(
    profile: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any] | None:
    desired_name = _normalize_school_name(profile.get("name") or profile.get("university_name"))
    desired_city = _normalize_simple(profile.get("city"))
    desired_state = _state_code(profile.get("state"))
    scored: list[tuple[int, int, dict[str, Any]]] = []

    for candidate in candidates:
        candidate_name = _normalize_school_name(candidate.get("name"))
        candidate_city = _normalize_simple(candidate.get("city"))
        candidate_state = _state_code(candidate.get("state"))
        score = 0
        if candidate_name == desired_name:
            score += 100
        elif candidate_name.startswith(desired_name) or desired_name in candidate_name:
            score += 70
        if desired_city and candidate_city == desired_city:
            score += 25
        if desired_state and candidate_state == desired_state:
            score += 15
        scored.append((score, candidate.get("size") or 0, candidate))

    if not scored:
        return None
    scored.sort(key=lambda item: (item[0], item[1]), reverse=True)
    best_score, _, best_match = scored[0]
    return best_match if best_score >= 70 else None


def _normalize_school_name(value: Any) -> str:
    text = _normalize_simple(value)
    text = re.sub(r"\bmain campus\b$", "", text).strip()
    return text


def _normalize_simple(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).lower()
    text = re.sub(r"[-_]+", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


client = CollegeScorecardClient()
