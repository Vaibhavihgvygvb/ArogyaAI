from app.ai.evidence.interfaces.coverage import CoverageAnalyzer
from app.ai.evidence.schemas import (
    CoverageGap,
    CoverageResult,
    EvidenceState,
    VerificationResult,
    VerificationStatus,
)


class CoverageAnalyzerEngine(CoverageAnalyzer):
    async def analyze(
        self,
        verification_results: list[VerificationResult],
        state: EvidenceState | None = None,
    ) -> CoverageResult:
        if not verification_results:
            return CoverageResult()

        total = len(verification_results)
        verified = sum(1 for v in verification_results if v.status == VerificationStatus.VERIFIED)
        unverified = sum(1 for v in verification_results if v.status == VerificationStatus.UNVERIFIED)
        partial = sum(1 for v in verification_results if v.status == VerificationStatus.PARTIALLY_VERIFIED)

        coverage_score = (verified + (partial * 0.5)) / total if total > 0 else 0.0
        evidence_density = sum(
            len(v.supporting_sources) + len(v.contradicting_sources)
            for v in verification_results
        ) / max(total, 1)

        gaps = self._find_gaps(verification_results)
        recommendations = self._make_recommendations(gaps, coverage_score)

        return CoverageResult(
            total_spans=total,
            verified_spans=verified,
            unverified_spans=unverified,
            partially_verified_spans=partial,
            coverage_score=round(coverage_score, 4),
            evidence_density=round(evidence_density, 2),
            gaps=gaps,
            recommendations=recommendations,
        )

    def _find_gaps(self, results: list[VerificationResult]) -> list[CoverageGap]:
        gaps = []
        for vr in results:
            if vr.status == VerificationStatus.UNVERIFIED:
                gaps.append(
                    CoverageGap(
                        claim=vr.span.claim,
                        gap_type="unverified",
                        severity="high",
                        description=f"No evidence found for claim: {vr.span.claim}",
                    )
                )
            elif vr.status == VerificationStatus.CONTRADICTED:
                gaps.append(
                    CoverageGap(
                        claim=vr.span.claim,
                        gap_type="contradicted",
                        severity="high",
                        description=f"Evidence contradicts claim: {vr.span.claim}",
                    )
                )
            elif vr.status == VerificationStatus.PARTIALLY_VERIFIED:
                gaps.append(
                    CoverageGap(
                        claim=vr.span.claim,
                        gap_type="insufficient",
                        severity="medium",
                        description=f"Limited evidence for claim: {vr.span.claim}",
                    )
                )
        return gaps

    def _make_recommendations(
        self, gaps: list[CoverageGap], score: float
    ) -> list[str]:
        recs = []
        if score < 0.5:
            recs.append("Increase evidence coverage to improve confidence.")
        if any(g.gap_type == "contradicted" for g in gaps):
            recs.append("Review contradicted claims against current medical guidelines.")
        if any(g.gap_type == "unverified" for g in gaps):
            recs.append("Add sources for unverified claims.")
        if any(g.gap_type == "insufficient" for g in gaps):
            recs.append("Include additional supporting references for partially verified claims.")
        if not recs:
            recs.append("Evidence coverage is adequate.")
        return recs
