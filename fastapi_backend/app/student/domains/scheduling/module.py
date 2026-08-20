from __future__ import annotations

from app.orchestrator.modules.base_module import BaseModule
from app.orchestrator.schemas.module_response import ModuleResponse
from app.orchestrator.schemas.student_context import StudentContext
from app.student.domains.scheduling.engine import (
    CandidateGenerator,
    CandidateValidationService,
    PreferenceScoringService,
    ScheduleMetricsService,
    ScheduleRankingService,
)
from app.student.domains.scheduling.services.retrieval_service import (
    SchedulePilotRetrievalService,
    schedulepilot_retrieval_service,
)

MODULE_NAME = "scheduling"
MODULE_DESCRIPTION = "Build and explain student course schedules."
MODULE_VERSION = "0.7.0"
IMPLEMENTATION_PHASE = "Phase 3C"


class SchedulePilotModule(BaseModule):
    """Orchestrator module shell for SchedulePilot scheduling workflows."""

    name = MODULE_NAME
    description = MODULE_DESCRIPTION

    def __init__(
        self,
        db=None,
        retrieval_service: SchedulePilotRetrievalService | None = None,
        candidate_generator: CandidateGenerator | None = None,
        validation_service: CandidateValidationService | None = None,
        metrics_service: ScheduleMetricsService | None = None,
        scoring_service: PreferenceScoringService | None = None,
        ranking_service: ScheduleRankingService | None = None,
    ) -> None:
        self.db = db
        self.retrieval_service = retrieval_service or schedulepilot_retrieval_service
        self.candidate_generator = candidate_generator or CandidateGenerator()
        self.validation_service = validation_service or CandidateValidationService()
        self.metrics_service = metrics_service or ScheduleMetricsService()
        self.scoring_service = scoring_service or PreferenceScoringService()
        self.ranking_service = ranking_service or ScheduleRankingService()

    async def execute(self, context: StudentContext, query: str) -> ModuleResponse:
        """Retrieve scheduling context and generate deterministic candidates."""
        if self.db is None:
            return ModuleResponse(
                module_name=self.name,
                content="Scheduling retrieval requires a database session.",
                data={},
                confidence=0.0,
                metadata={
                    "description": self.description,
                    "module_version": MODULE_VERSION,
                    "implementation_phase": IMPLEMENTATION_PHASE,
                    "status": "error",
                    "error": "database_session_required",
                },
            )

        user = context.user or {}
        plan = context.plan or {}
        user_id = user.get("id")
        plan_id = plan.get("plan_id")
        if not isinstance(user_id, int) or not plan_id:
            return ModuleResponse(
                module_name=self.name,
                content="Scheduling retrieval requires a loaded user and plan context.",
                data={},
                confidence=0.0,
                metadata={
                    "description": self.description,
                    "module_version": MODULE_VERSION,
                    "implementation_phase": IMPLEMENTATION_PHASE,
                    "status": "error",
                    "error": "student_context_required",
                },
            )

        retrieval_context = await self.retrieval_service.build_context(
            self.db,
            user_id=user_id,
            plan_id=str(plan_id),
        )
        generation_result = self.candidate_generator.generate(retrieval_context)
        validated_candidates, validation_metadata = (
            self.validation_service.validate_generation_result(generation_result)
        )
        enriched_candidates, metrics_metadata = self.metrics_service.compute_for_candidates(
            validated_candidates
        )
        scored_candidates, scoring_metadata = self.scoring_service.score_candidates(
            enriched_candidates,
            context.preferences,
        )
        ranking_result = self.ranking_service.rank_candidates(scored_candidates)
        data = retrieval_context.model_dump(mode="json")
        data["candidates"] = [candidate.model_dump(mode="json") for candidate in scored_candidates]
        data["validated_candidates"] = data["candidates"]
        data["scored_candidates"] = data["candidates"]
        data["ranked_options"] = [
            option.model_dump(mode="json") for option in ranking_result.options
        ]
        data["top_option"] = (
            ranking_result.top_option.model_dump(mode="json")
            if ranking_result.top_option is not None
            else None
        )
        data["generation_metadata"] = generation_result.metadata.model_dump(mode="json")
        data["generation_warnings"] = list(generation_result.warnings)
        data["validation_metadata"] = validation_metadata
        data["metrics_metadata"] = metrics_metadata
        data["scoring_metadata"] = scoring_metadata
        data["ranking_metadata"] = ranking_result.metadata.model_dump(mode="json")
        return ModuleResponse(
            module_name=self.name,
            content=(
                "Schedule candidates generated, validated, scored, and ranked "
                "successfully.\n\n"
                "Persistence and schedule activation have not yet been implemented."
            ),
            data=data,
            confidence=0.75,
            metadata={
                "description": self.description,
                "module_version": MODULE_VERSION,
                "implementation_phase": IMPLEMENTATION_PHASE,
                "status": "options_ranked",
                "query": query,
                "counts": {
                    "courses": len(retrieval_context.courses),
                    "terms": len(retrieval_context.terms),
                    "offerings": len(retrieval_context.offerings),
                    "sections": len(retrieval_context.sections),
                    "meetings": len(retrieval_context.meetings),
                    "candidates": len(scored_candidates),
                    "scored_candidates": len(scored_candidates),
                    "ranked_options": len(ranking_result.options),
                    "feasible_candidates": validation_metadata["feasible_count"],
                    "infeasible_candidates": validation_metadata["infeasible_count"],
                },
                "candidate_generation_implemented": True,
                "conflict_detection_implemented": True,
                "feasibility_validation_implemented": True,
                "metrics_implemented": True,
                "scoring_implemented": True,
                "ranking_implemented": True,
                "persistence_implemented": False,
            },
        )
