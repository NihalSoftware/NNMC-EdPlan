from __future__ import annotations

import re
from time import perf_counter
from typing import Any

from app.student.domains.scheduling.engine.candidate_models import (
    PreferenceEvaluation,
    ScheduleCandidate,
    ScheduleScoringSummary,
)
from app.student.domains.scheduling.engine.default_scoring_weights import (
    DEFAULT_SCORING_WEIGHTS,
    ScoringWeights,
)


class PreferenceScorer:
    """Deterministically scores candidates from objective metrics and preferences."""

    def __init__(self, weights: ScoringWeights | None = None) -> None:
        self.weights = weights or DEFAULT_SCORING_WEIGHTS

    def score(
        self, candidate: ScheduleCandidate, preferences: list[dict[str, Any]]
    ) -> ScheduleCandidate:
        started_at = perf_counter()
        normalized_preferences = normalize_preferences(preferences)
        evaluations: list[PreferenceEvaluation] = []

        if candidate.is_feasible is False:
            evaluations.append(
                PreferenceEvaluation(
                    preference_key="candidate_feasibility",
                    satisfied=False,
                    score_delta=self.weights.infeasible_penalty,
                    rationale="Candidate is infeasible due to validation conflicts.",
                )
            )

        for key, value in normalized_preferences.items():
            if key not in self.weights.supported_preferences:
                continue
            evaluation = self._evaluate(candidate, key, value)
            if evaluation is not None:
                evaluations.append(evaluation)

        bonus_total = sum(item.score_delta for item in evaluations if item.score_delta > 0)
        penalty_total = sum(item.score_delta for item in evaluations if item.score_delta < 0)
        raw_score = self.weights.base_score + bonus_total + penalty_total
        normalized_score = _clamp(raw_score, self.weights.min_score, self.weights.max_score)
        scoring_time_ms = max(0, round((perf_counter() - started_at) * 1000))
        return candidate.model_copy(
            update={
                "score": raw_score,
                "normalized_score": normalized_score,
                "scoring_summary": ScheduleScoringSummary(
                    scoring_version="1.0",
                    scoring_time_ms=scoring_time_ms,
                    evaluated_preferences=len(evaluations),
                    applied_bonus_count=len([item for item in evaluations if item.score_delta > 0]),
                    applied_penalty_count=len(
                        [item for item in evaluations if item.score_delta < 0]
                    ),
                    bonus_total=bonus_total,
                    penalty_total=penalty_total,
                    satisfied_preferences=[
                        item.preference_key for item in evaluations if item.satisfied
                    ],
                    violated_preferences=[
                        item.preference_key for item in evaluations if not item.satisfied
                    ],
                    evaluations=evaluations,
                ),
            },
            deep=True,
        )

    def _evaluate(
        self,
        candidate: ScheduleCandidate,
        key: str,
        value: Any,
    ) -> PreferenceEvaluation | None:
        metrics = candidate.metrics
        if metrics is None:
            return None

        if key == "morning_classes":
            satisfied = (
                metrics.latest_end_time is not None
                and metrics.latest_end_time.hour <= self.weights.morning_end_hour
            )
            return self._binary(key, satisfied, "Prefers schedules ending by noon.")
        if key == "afternoon_classes":
            satisfied = (
                metrics.earliest_start_time is not None
                and metrics.earliest_start_time.hour >= self.weights.afternoon_start_hour
                and metrics.latest_end_time is not None
                and metrics.latest_end_time.hour <= self.weights.afternoon_end_hour
            )
            return self._binary(key, satisfied, "Prefers afternoon class blocks.")
        if key == "evening_classes":
            satisfied = (
                metrics.earliest_start_time is not None
                and metrics.earliest_start_time.hour >= self.weights.evening_start_hour
            )
            return self._binary(key, satisfied, "Prefers evening classes.")
        if key in {"no_friday", "friday_only_if_required"}:
            satisfied = metrics.friday_classes == 0
            return self._binary(key, satisfied, "Prefers avoiding Friday classes.")
        if key in {"minimize_campus_days", "maximize_free_days"}:
            extra_days = max(0, metrics.campus_days - self.weights.preferred_max_campus_days)
            if extra_days == 0:
                return self._binary(key, True, "Campus days are within preferred limit.")
            return PreferenceEvaluation(
                preference_key=key,
                satisfied=False,
                score_delta=self.weights.campus_day_penalty * extra_days,
                rationale=f"Schedule uses {metrics.campus_days} campus days.",
            )
        if key == "online_only":
            satisfied = (
                metrics.total_sections > 0
                and metrics.online_section_count == metrics.total_sections
            )
            return self._binary(key, satisfied, "Requires all sections to be online.")
        if key == "online_preferred":
            return self._mode_preference(key, metrics.online_section_count, metrics.total_sections)
        if key == "hybrid_preferred":
            return self._mode_preference(key, metrics.hybrid_section_count, metrics.total_sections)
        if key == "in_person_preferred":
            return self._mode_preference(
                key, metrics.in_person_section_count, metrics.total_sections
            )
        if key == "minimize_gaps":
            if metrics.total_gap_minutes <= self.weights.compact_gap_threshold_minutes:
                return self._binary(key, True, "Schedule has limited gaps.")
            penalty = (
                (metrics.total_gap_minutes - self.weights.compact_gap_threshold_minutes)
                / 60
                * abs(self.weights.gap_penalty_per_hour)
            )
            return PreferenceEvaluation(
                preference_key=key,
                satisfied=False,
                score_delta=-round(penalty, 2),
                rationale=f"Schedule has {metrics.total_gap_minutes} gap minutes.",
            )
        if key == "maximize_back_to_back_classes":
            satisfied = metrics.total_gap_minutes == 0 and metrics.synchronous_meetings > 1
            return self._binary(key, satisfied, "Prefers back-to-back classes.")
        if key == "avoid_large_breaks":
            max_gap = metrics.maximum_gap_minutes or 0
            satisfied = max_gap <= self.weights.large_break_threshold_minutes
            return self._binary(key, satisfied, "Avoids large breaks between classes.")
        if key == "minimum_credits":
            minimum = _first_int(value)
            if minimum is None:
                return None
            return self._binary(
                key,
                metrics.total_credits >= minimum,
                f"Requires at least {minimum} credits.",
            )
        if key == "maximum_credits":
            maximum = _first_int(value)
            if maximum is None:
                return None
            return self._binary(
                key,
                metrics.total_credits <= maximum,
                f"Requires at most {maximum} credits.",
            )
        if key == "preferred_credit_range":
            credit_range = _credit_range(value)
            if credit_range is None:
                return None
            minimum, maximum = credit_range
            return self._binary(
                key,
                minimum <= metrics.total_credits <= maximum,
                f"Prefers {minimum}-{maximum} credits.",
            )
        if key == "prefer_available_seats":
            if metrics.open_seat_ratio is None:
                return PreferenceEvaluation(
                    preference_key=key,
                    satisfied=False,
                    score_delta=self.weights.small_penalty,
                    rationale="Seat availability is unavailable.",
                )
            delta = round(metrics.open_seat_ratio * self.weights.seat_availability_bonus, 2)
            return PreferenceEvaluation(
                preference_key=key,
                satisfied=metrics.open_seat_ratio > 0,
                score_delta=delta if metrics.open_seat_ratio > 0 else self.weights.small_penalty,
                rationale="Prefers schedules with higher seat availability.",
            )
        return None

    def _binary(self, key: str, satisfied: bool, rationale: str) -> PreferenceEvaluation:
        return PreferenceEvaluation(
            preference_key=key,
            satisfied=satisfied,
            score_delta=(
                self.weights.satisfied_bonus if satisfied else self.weights.violation_penalty
            ),
            rationale=rationale,
        )

    def _mode_preference(
        self,
        key: str,
        matching_sections: int,
        total_sections: int,
    ) -> PreferenceEvaluation:
        if total_sections <= 0:
            return PreferenceEvaluation(
                preference_key=key,
                satisfied=False,
                score_delta=self.weights.small_penalty,
                rationale="No sections available to evaluate delivery mode.",
            )
        ratio = matching_sections / total_sections
        if ratio == 0:
            return PreferenceEvaluation(
                preference_key=key,
                satisfied=False,
                score_delta=self.weights.violation_penalty,
                rationale="No sections match preferred delivery mode.",
            )
        return PreferenceEvaluation(
            preference_key=key,
            satisfied=True,
            score_delta=round(self.weights.satisfied_bonus * ratio, 2),
            rationale="Some or all sections match preferred delivery mode.",
        )


def normalize_preferences(preferences: list[dict[str, Any]]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for preference in preferences:
        key = str(preference.get("key") or preference.get("preference_key") or "").strip()
        value = preference.get("value", preference.get("preference_value"))
        normalized_key = _normalize_key(key, value)
        if normalized_key:
            normalized[normalized_key] = value if value is not None else True
    return normalized


def _normalize_key(key: str, value: Any) -> str | None:
    lowered_key = key.lower().strip()
    lowered_value = str(value or "").lower().strip()
    combined = f"{lowered_key} {lowered_value}"
    explicit_keys = {
        "morning_classes",
        "afternoon_classes",
        "evening_classes",
        "no_friday",
        "friday_only_if_required",
        "minimize_campus_days",
        "maximize_free_days",
        "online_only",
        "online_preferred",
        "hybrid_preferred",
        "in_person_preferred",
        "minimize_gaps",
        "maximize_back_to_back_classes",
        "avoid_large_breaks",
        "minimum_credits",
        "maximum_credits",
        "preferred_credit_range",
        "prefer_available_seats",
    }
    if lowered_key in explicit_keys:
        return lowered_key
    if "morning" in combined:
        return "morning_classes"
    if "afternoon" in combined:
        return "afternoon_classes"
    if "evening" in combined or "night" in combined:
        return "evening_classes"
    if "no classes on friday" in combined or "no friday" in combined:
        return "no_friday"
    if "friday only" in combined:
        return "friday_only_if_required"
    if "compact" in combined:
        return "minimize_gaps"
    if "back-to-back" in combined or "back to back" in combined:
        return "maximize_back_to_back_classes"
    if "large break" in combined:
        return "avoid_large_breaks"
    if "online only" in combined:
        return "online_only"
    if "online" in combined:
        return "online_preferred"
    if "hybrid" in combined:
        return "hybrid_preferred"
    if "in-person" in combined or "in person" in combined:
        return "in_person_preferred"
    if "seat" in combined or "availability" in combined:
        return "prefer_available_seats"
    if "credit" in combined and "-" in lowered_value:
        return "preferred_credit_range"
    if "minimum" in combined and "credit" in combined:
        return "minimum_credits"
    if "maximum" in combined and "credit" in combined:
        return "maximum_credits"
    return None


def _first_int(value: Any) -> int | None:
    match = re.search(r"\d+", str(value))
    return int(match.group(0)) if match else None


def _credit_range(value: Any) -> tuple[int, int] | None:
    matches = re.findall(r"\d+", str(value))
    if len(matches) < 2:
        return None
    first, second = int(matches[0]), int(matches[1])
    return (min(first, second), max(first, second))


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return round(max(minimum, min(maximum, value)), 2)
