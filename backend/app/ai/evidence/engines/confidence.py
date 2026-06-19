from app.ai.evidence.interfaces.confidence import ConfidenceCalculator
from app.ai.evidence.schemas import (
    Citation,
    ConfidenceBreakdown,
    ConfidenceResult,
    ConflictResult,
    CoverageResult,
    EvidenceState,
    VerificationResult,
    VerificationStatus,
)


class ConfidenceCalculatorEngine(ConfidenceCalculator):
    VERIFICATION_WEIGHT = 0.35
    CITATION_WEIGHT = 0.20
    COVERAGE_WEIGHT = 0.25
    SOURCE_QUALITY_WEIGHT = 0.20

    async def calculate(
        self,
        verification_results: list[VerificationResult],
        coverage: CoverageResult | None = None,
        conflicts: list[ConflictResult] | None = None,
        citations: list[Citation] | None = None,
        state: EvidenceState | None = None,
    ) -> ConfidenceResult:
        v_conf = self._verification_confidence(verification_results)
        c_conf = self._citation_confidence(citations) if citations else 1.0
        cov_conf = self._coverage_confidence(coverage) if coverage else 0.0
        q_conf = self._source_quality_confidence(verification_results)

        penalty = self._conflict_penalty(conflicts) if conflicts else 0.0

        overall = (
            self.VERIFICATION_WEIGHT * v_conf
            + self.CITATION_WEIGHT * c_conf
            + self.COVERAGE_WEIGHT * cov_conf
            + self.SOURCE_QUALITY_WEIGHT * q_conf
        ) * (1.0 - penalty)

        overall = round(max(0.0, min(1.0, overall)), 4)

        suitable = overall >= 0.4

        warnings = []
        if v_conf < 0.3:
            warnings.append("Low verification confidence.")
        if cov_conf < 0.3:
            warnings.append("Insufficient evidence coverage.")
        if conflicts and len(conflicts) > 2:
            warnings.append(f"Multiple conflicts detected ({len(conflicts)}).")
        if not suitable:
            warnings.append("Overall confidence below suitable-for-AI threshold.")

        breakdown = [
            ConfidenceBreakdown(category="Verification", score=v_conf, weight=self.VERIFICATION_WEIGHT),
            ConfidenceBreakdown(category="Citation", score=c_conf, weight=self.CITATION_WEIGHT),
            ConfidenceBreakdown(category="Coverage", score=cov_conf, weight=self.COVERAGE_WEIGHT),
            ConfidenceBreakdown(category="Source Quality", score=q_conf, weight=self.SOURCE_QUALITY_WEIGHT),
        ]

        return ConfidenceResult(
            overall=overall,
            verification_confidence=v_conf,
            citation_confidence=c_conf,
            coverage_confidence=cov_conf,
            source_quality_confidence=q_conf,
            suitable_for_ai=suitable,
            breakdown=breakdown,
            warnings=warnings,
        )

    def _verification_confidence(self, results: list[VerificationResult]) -> float:
        if not results:
            return 0.0
        scores = [
            r.confidence
            for r in results
            if r.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED)
        ]
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def _citation_confidence(self, citations: list[Citation]) -> float:
        if not citations:
            return 0.0
        scores = [c.confidence for c in citations if c.confidence]
        if not scores:
            return 0.0
        return sum(scores) / len(scores)

    def _coverage_confidence(self, coverage: CoverageResult) -> float:
        return coverage.coverage_score

    def _source_quality_confidence(self, results: list[VerificationResult]) -> float:
        sources = []
        for vr in results:
            sources.extend(vr.supporting_sources)
            sources.extend(vr.contradicting_sources)
        if not sources:
            return 0.0
        scores = [
            (s.authority_score + s.relevance_score + s.recency_score + s.quality_score) / 4.0
            for s in sources
        ]
        return sum(scores) / len(scores)

    def _conflict_penalty(self, conflicts: list[ConflictResult]) -> float:
        if not conflicts:
            return 0.0
        severities = {"high": 0.15, "medium": 0.08, "low": 0.03}
        total = sum(severities.get(c.severity, 0.05) for c in conflicts)
        return min(total, 0.5)
