from __future__ import annotations

from app.student.domains.scheduling.engine.candidate_models import (
    ScheduleCandidate,
    ScheduleOption,
)
from app.student.domains.scheduling.engine.ranking_config import (
    DEFAULT_RANKING_CONFIG,
    ScheduleRankingConfig,
)


class ScheduleRankingEngine:
    """Ranks scored feasible candidates into student-facing schedule options."""

    def __init__(self, config: ScheduleRankingConfig | None = None) -> None:
        self.config = config or DEFAULT_RANKING_CONFIG

    def rank(self, candidates: list[ScheduleCandidate]) -> tuple[list[ScheduleOption], int]:
        feasible_candidates = [
            candidate for candidate in candidates if candidate.is_feasible is True
        ]
        sorted_candidates = sorted(feasible_candidates, key=_ranking_key)
        selected_candidates: list[ScheduleCandidate] = []
        seen_signatures: set[tuple[str, ...]] = set()
        duplicate_count = 0

        for candidate in sorted_candidates:
            signature = _section_signature(candidate)
            if self.config.enforce_unique_section_sets and signature in seen_signatures:
                duplicate_count += 1
                continue
            seen_signatures.add(signature)
            selected_candidates.append(candidate)
            if len(selected_candidates) >= self.config.max_options:
                break

        return [
            self._to_option(candidate, rank=index + 1)
            for index, candidate in enumerate(selected_candidates)
        ], duplicate_count

    def _to_option(self, candidate: ScheduleCandidate, *, rank: int) -> ScheduleOption:
        section_signature = _section_signature(candidate)
        return ScheduleOption(
            option_id=f"schedule-option-{rank:06d}",
            rank=rank,
            score=candidate.score,
            normalized_score=candidate.normalized_score,
            selected_sections=list(candidate.sections),
            selected_meetings=list(candidate.meetings),
            metrics=candidate.metrics,
            warnings=list(candidate.warnings),
            conflicts=list(candidate.conflicts),
            explanation=_explanation(candidate),
            tradeoffs=_tradeoffs(candidate),
            metadata={
                "source_candidate_id": candidate.candidate_id,
                "section_signature": list(section_signature),
                "ranking_version": "1.0",
            },
        )


def _ranking_key(candidate: ScheduleCandidate) -> tuple:
    metrics = candidate.metrics
    return (
        -(candidate.normalized_score if candidate.normalized_score is not None else 0),
        len(candidate.conflicts),
        len(candidate.warnings),
        metrics.total_gap_minutes if metrics is not None else 0,
        metrics.campus_days if metrics is not None else 0,
        candidate.candidate_id,
    )


def _section_signature(candidate: ScheduleCandidate) -> tuple[str, ...]:
    return tuple(sorted(section.section_id for section in candidate.sections))


def _explanation(candidate: ScheduleCandidate) -> str:
    score = candidate.normalized_score if candidate.normalized_score is not None else 0
    satisfied_count = len(candidate.scoring_summary.satisfied_preferences)
    violated_count = len(candidate.scoring_summary.violated_preferences)

    if score >= 75:
        return (
            "This schedule ranked highly because it satisfies most of your stated " "preferences."
        )
    if score >= 50 and satisfied_count >= violated_count:
        return (
            "This schedule is a balanced option based on your preferences and the "
            "available sections."
        )
    return (
        "This schedule is feasible, but it ranked lower because it has more trade-offs "
        "against your stated preferences."
    )


def _tradeoffs(candidate: ScheduleCandidate) -> list[str]:
    metrics = candidate.metrics
    if metrics is None:
        return ["Metrics unavailable for trade-off analysis"]

    tradeoffs: list[str] = []
    if metrics.friday_classes > 0:
        tradeoffs.append("Friday class included")
    if (metrics.maximum_gap_minutes or 0) > 90:
        tradeoffs.append("Long gap included")
    if metrics.latest_end_time is not None and metrics.latest_end_time.hour >= 17:
        tradeoffs.append("Evening class included")
    if metrics.hybrid_section_count > 0:
        tradeoffs.append("Hybrid delivery included")
    if metrics.online_section_count > 0:
        tradeoffs.append("Online delivery included")
    if metrics.campus_days > 3:
        tradeoffs.append(f"Uses {metrics.campus_days} campus days")
    if metrics.open_seat_ratio is not None and metrics.open_seat_ratio >= 0.5:
        tradeoffs.append("High seat availability")
    if metrics.open_seat_ratio is not None and metrics.open_seat_ratio < 0.2:
        tradeoffs.append("Limited seat availability")
    if candidate.warnings:
        tradeoffs.append("Includes non-critical schedule warnings")
    return tradeoffs or ["No major trade-offs detected"]
