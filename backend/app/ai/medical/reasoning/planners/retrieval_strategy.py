import math

from app.ai.medical.engine.schemas import QueryUnderstandingResult
from app.ai.medical.reasoning.exceptions.exceptions import RetrievalStrategyError
from app.ai.medical.reasoning.interfaces.interfaces import RetrievalStrategyABC
from app.ai.medical.reasoning.schemas.schemas import (
    EvidencePlan,
    RetrievalPlan,
    RetrievalStrategyType,
)


class RetrievalStrategy(RetrievalStrategyABC):
    async def plan(
        self,
        query: str,
        evidence_plan: EvidencePlan,
        analysis: QueryUnderstandingResult,
        top_k: int = 15,
        filters: dict | None = None,
    ) -> RetrievalPlan:
        if not query or not query.strip():
            raise RetrievalStrategyError("Query cannot be empty")

        sub_queries = list(evidence_plan.retrieval_queries)
        if not sub_queries:
            sub_queries = [query]

        strategy = self._determine_strategy(sub_queries, analysis)
        weights = self._compute_weights(sub_queries, strategy, evidence_plan)
        merge_strategy = self._determine_merge_strategy(analysis)
        top_k_per_query = max(1, top_k // len(sub_queries)) if sub_queries else top_k

        merged_filters = dict(evidence_plan.priority_filters or {})
        if filters:
            merged_filters.update(filters)

        return RetrievalPlan(
            strategy=strategy,
            sub_queries=sub_queries,
            weights=weights,
            top_k_per_query=min(top_k_per_query, 20),
            merge_strategy=merge_strategy,
            filters=merged_filters if merged_filters else None,
        )

    def _determine_strategy(
        self,
        sub_queries: list[str],
        analysis: QueryUnderstandingResult,
    ) -> RetrievalStrategyType:
        if len(sub_queries) <= 1:
            return RetrievalStrategyType.SINGLE

        if analysis.urgency and analysis.urgency.is_emergency:
            return RetrievalStrategyType.PARALLEL

        if analysis.intent and analysis.intent.primary_intent:
            intent = analysis.intent.primary_intent.intent_type
            if intent in ("medication_information", "disease_information"):
                return RetrievalStrategyType.PARALLEL
            if intent in ("differential_diagnosis", "comparative_analysis"):
                return RetrievalStrategyType.HIERARCHICAL

        if len(sub_queries) <= 3:
            return RetrievalStrategyType.PARALLEL

        return RetrievalStrategyType.HIERARCHICAL

    def _compute_weights(
        self,
        sub_queries: list[str],
        strategy: RetrievalStrategyType,
        evidence_plan: EvidencePlan,
    ) -> list[float]:
        n = len(sub_queries)
        if n == 0:
            return []

        if strategy == RetrievalStrategyType.SINGLE:
            return [1.0]

        weights = [1.0] * n

        for i, sq in enumerate(sub_queries):
            for req in evidence_plan.evidence_requirements:
                for variation in req.query_variations:
                    if sq.lower().startswith(variation.lower()[:20]):
                        if req.required:
                            weights[i] = 3.0
                        elif req.priority.value == "essential":
                            weights[i] = 2.5
                        elif req.priority.value == "high":
                            weights[i] = 2.0
                        break

        if strategy == RetrievalStrategyType.HIERARCHICAL:
            for i in range(1, n):
                weights[i] *= 0.8

        total = sum(weights)
        if total > 0:
            weights = [w / total * n for w in weights]

        return [round(w, 3) for w in weights]

    def _determine_merge_strategy(self, analysis: QueryUnderstandingResult) -> str:
        if analysis.urgency and analysis.urgency.is_emergency:
            return "max"
        if analysis.intent and analysis.intent.primary_intent:
            intent = analysis.intent.primary_intent.intent_type
            if intent in ("medication_information", "disease_information"):
                return "score_weighted"
        return "round_robin"
