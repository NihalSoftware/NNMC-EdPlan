from __future__ import annotations

from time import perf_counter

from app.student.domains.scheduling.engine.candidate_models import (
    ScheduleCandidate,
    ScheduleGenerationResult,
)
from app.student.domains.scheduling.engine.feasibility_validator import FeasibilityValidator


class CandidateValidationService:
    """Validates generated schedule candidates without filtering or ranking them."""

    def __init__(self, validator: FeasibilityValidator | None = None) -> None:
        self.validator = validator or FeasibilityValidator()

    def validate_generation_result(
        self,
        generation_result: ScheduleGenerationResult,
    ) -> tuple[list[ScheduleCandidate], dict]:
        started_at = perf_counter()
        candidates = self.validator.validate_many(generation_result.candidates)
        validation_time_ms = max(0, round((perf_counter() - started_at) * 1000))
        feasible_count = len([candidate for candidate in candidates if candidate.is_feasible])
        infeasible_count = len(candidates) - feasible_count
        warning_count = sum(candidate.validation_summary.warning_count for candidate in candidates)
        conflict_count = sum(
            candidate.validation_summary.conflict_count for candidate in candidates
        )
        return candidates, {
            "validated_count": len(candidates),
            "feasible_count": feasible_count,
            "infeasible_count": infeasible_count,
            "conflict_count": conflict_count,
            "warning_count": warning_count,
            "validation_time_ms": validation_time_ms,
        }
