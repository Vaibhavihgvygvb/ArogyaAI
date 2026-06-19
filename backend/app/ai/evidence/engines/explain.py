from app.ai.evidence.interfaces.explain import ExplainabilityProvider
from app.ai.evidence.schemas import (
    Citation,
    ConflictResult,
    ConfidenceResult,
    CoverageResult,
    EvidenceState,
    ExplanationComponent,
    ExplanationResult,
    VerificationResult,
    VerificationStatus,
)


class ExplainabilityProviderEngine(ExplainabilityProvider):
    async def explain(
        self,
        verification_results: list[VerificationResult],
        coverage: CoverageResult | None = None,
        conflicts: list[ConflictResult] | None = None,
        confidence: ConfidenceResult | None = None,
        citations: list[Citation] | None = None,
        state: EvidenceState | None = None,
    ) -> ExplanationResult:
        total = len(verification_results)
        verified = sum(1 for v in verification_results if v.status == VerificationStatus.VERIFIED)

        n_verified = verified
        n_total = total
        n_conflicts = len(conflicts) if conflicts else 0

        components = [
            ExplanationComponent(
                component="Verification",
                detail=f"{n_verified}/{n_total} claims verified",
                score=float(n_verified) / max(n_total, 1),
            ),
            ExplanationComponent(
                component="Coverage",
                detail=(
                    f"Coverage score: {coverage.coverage_score:.2f}"
                    if coverage
                    else "Not analyzed"
                ),
                score=coverage.coverage_score if coverage else 0.0,
            ),
            ExplanationComponent(
                component="Conflicts",
                detail=f"{n_conflicts} conflict(s) detected",
                score=1.0 - min(n_conflicts * 0.2, 1.0),
            ),
        ]

        if confidence:
            components.append(
                ExplanationComponent(
                    component="Confidence",
                    detail=f"Overall: {confidence.overall:.2f}",
                    score=confidence.overall,
                )
            )

        narrative = self._build_narrative(verification_results, coverage, conflicts, confidence)

        return ExplanationResult(
            summary=f"Analyzed {n_total} evidence spans: {n_verified} verified, {n_conflicts} conflicts.",
            components=components,
            narrative=narrative,
            verification_summary=self._verification_summary(verification_results),
            citation_summary=f"{len(citations) if citations else 0} citations generated" if citations else "No citations",
            coverage_summary=(
                f"Coverage: {coverage.coverage_score:.1%}" if coverage else "Not analyzed"
            ),
            conflict_summary=f"{n_conflicts} conflict(s) found",
            confidence_summary=(
                f"Confidence: {confidence.overall:.1%}" if confidence else "Not calculated"
            ),
            recommendations=[],
        )

    def _build_narrative(
        self,
        results: list[VerificationResult],
        coverage: CoverageResult | None,
        conflicts: list[ConflictResult] | None,
        confidence: ConfidenceResult | None,
    ) -> str:
        parts = []
        verified = sum(1 for r in results if r.status == VerificationStatus.VERIFIED)
        parts.append(f"Out of {len(results)} claims, {verified} were verified.")

        if coverage:
            parts.append(f"Evidence coverage is at {coverage.coverage_score:.0%}.")
        if conflicts:
            parts.append(f"{len(conflicts)} evidence conflicts were identified.")
        if confidence:
            parts.append(f"Overall confidence score: {confidence.overall:.0%}.")
        return " ".join(parts)

    def _verification_summary(self, results: list[VerificationResult]) -> str:
        if not results:
            return "No evidence to verify."
        counts = {
            status: sum(1 for r in results if r.status == status)
            for status in VerificationStatus
        }
        return (
            f"Verified: {counts[VerificationStatus.VERIFIED]}, "
            f"Partially: {counts[VerificationStatus.PARTIALLY_VERIFIED]}, "
            f"Unverified: {counts[VerificationStatus.UNVERIFIED]}, "
            f"Contradicted: {counts[VerificationStatus.CONTRADICTED]}"
        )
