from app.ai.medical.engine.schemas import QueryUnderstandingResult
from app.ai.medical.reasoning.exceptions.exceptions import ConfidencePlanningError
from app.ai.medical.reasoning.interfaces.interfaces import (
    RETRIEVAL_RESULT_TYPE,
    ConfidencePlannerABC,
)
from app.ai.medical.reasoning.schemas.schemas import ConfidencePlan, RankedContext


class ConfidencePlanner(ConfidencePlannerABC):
    async def plan(
        self,
        results: list[RETRIEVAL_RESULT_TYPE],
        ranked_context: RankedContext,
        analysis: QueryUnderstandingResult,
    ) -> ConfidencePlan:
        retrieval_confidence = self._compute_retrieval_confidence(results, ranked_context)
        factors = self._identify_factors(results, ranked_context, analysis)
        thresholds = self._compute_thresholds(analysis)

        min_confidence = 0.3
        if analysis.intent and analysis.intent.primary_intent:
            intent = analysis.intent.primary_intent.intent_type
            if intent in ("emergency", "prescription_explanation", "medication_information"):
                min_confidence = 0.5

        return ConfidencePlan(
            expected_retrieval_confidence=round(retrieval_confidence, 4),
            min_expected_confidence=min_confidence,
            confidence_factors=factors,
            confidence_thresholds=thresholds,
        )

    def _compute_retrieval_confidence(
        self,
        results: list[RETRIEVAL_RESULT_TYPE],
        ranked_context: RankedContext,
    ) -> float:
        if not results:
            return 0.0
        if not ranked_context.ranking_scores:
            return 0.0

        scores = ranked_context.ranking_scores
        avg_score = sum(scores) / len(scores)
        coverage = ranked_context.retained / max(ranked_context.total_original, 1)

        sample_score = 0.0
        if results:
            first = results[0]
            sample_score = getattr(first, "score", 0) or 0

        confidence = avg_score * 0.5 + coverage * 0.3 + min(sample_score, 1.0) * 0.2
        return max(0.0, min(1.0, confidence))

    def _identify_factors(
        self,
        results: list[RETRIEVAL_RESULT_TYPE],
        ranked_context: RankedContext,
        analysis: QueryUnderstandingResult,
    ) -> list[str]:
        factors = []

        if results:
            factors.append(f"Total results retrieved: {len(results)}")
        if ranked_context.total_original > 0:
            retention = (ranked_context.retained / ranked_context.total_original) * 100
            factors.append(f"Context retention rate: {retention:.0f}%")
        if ranked_context.ranking_scores:
            avg = sum(ranked_context.ranking_scores) / len(ranked_context.ranking_scores)
            factors.append(f"Average relevance score: {avg:.3f}")

        if analysis.intent and analysis.intent.primary_intent:
            factors.append(f"Intent confidence: {analysis.intent.primary_intent.confidence:.2f}")
        if analysis.specialty and analysis.specialty.primary_specialty:
            factors.append(
                f"Specialty match: {analysis.specialty.primary_specialty.specialty} "
                f"(confidence: {analysis.specialty.primary_specialty.confidence:.2f})"
            )
        if analysis.entities and analysis.entities.total > 0:
            factors.append(f"Entities extracted: {analysis.entities.total}")

        return factors

    def _compute_thresholds(self, analysis: QueryUnderstandingResult) -> dict[str, float]:
        thresholds: dict[str, float] = {
            "retrieval_confidence": 0.3,
            "evidence_coverage": 0.4,
            "citation_confidence": 0.3,
        }

        if analysis.urgency and analysis.urgency.level in ("critical", "high"):
            thresholds["retrieval_confidence"] = 0.5
            thresholds["evidence_coverage"] = 0.6

        if analysis.intent and analysis.intent.primary_intent:
            intent = analysis.intent.primary_intent.intent_type
            if intent in ("treatment_planning", "prescription_explanation"):
                thresholds["retrieval_confidence"] = 0.6
                thresholds["evidence_coverage"] = 0.7

        return thresholds
