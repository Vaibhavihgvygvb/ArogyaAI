import re

from app.ai.clinical_safety.exceptions import UnsupportedClaimError
from app.ai.clinical_safety.interfaces.unsupported import UnsupportedClaimDetector
from app.ai.clinical_safety.schemas import (
    SupportLevel,
    UnsupportedClaim,
    UnsupportedClaimReport,
)


class DefaultUnsupportedClaimDetector(UnsupportedClaimDetector):

    STOP_WORDS = frozenset({
        "the", "a", "an", "is", "are", "was", "were", "has", "have",
        "had", "do", "does", "did", "will", "would", "could", "should",
        "may", "might", "can", "shall", "to", "of", "in", "for", "on",
        "with", "at", "by", "from", "as", "into", "through", "during",
        "before", "after", "above", "below", "between", "this", "that",
        "these", "those", "it", "its", "and", "but", "or", "not", "no",
        "nor", "so", "yet", "be", "been", "being", "very", "too",
    })

    def __init__(self, config=None):
        self.max_claims = (
            getattr(config, 'CLINICAL_SAFETY_MAX_CLAIMS', 100)
            if config else 100
        )

    async def detect(
        self,
        claims: list[str],
        evidence: dict | None = None,
    ) -> UnsupportedClaimReport:
        try:
            if not claims:
                return UnsupportedClaimReport(
                    claims=[], total_claims=0, supported_count=0,
                    unsupported_count=0, contradictory_count=0,
                    coverage_score=0.0, passed=True,
                    summary="No claims to analyze.",
                )

            claims = claims[:self.max_claims]
            results: list[UnsupportedClaim] = [
                self._assess_claim(claim, evidence) for claim in claims
            ]

            total = len(results)
            supported = sum(
                1 for r in results
                if r.support_level == SupportLevel.FULLY_SUPPORTED
            )
            unsupported = sum(
                1 for r in results
                if r.support_level == SupportLevel.UNSUPPORTED
            )
            contradictory = sum(
                1 for r in results
                if r.support_level == SupportLevel.CONTRADICTORY
            )
            coverage = supported / total if total > 0 else 0.0

            return UnsupportedClaimReport(
                claims=results,
                total_claims=total,
                supported_count=supported,
                unsupported_count=unsupported,
                contradictory_count=contradictory,
                coverage_score=coverage,
                passed=coverage >= 0.5,
                summary=(
                    f"{supported}/{total} claims supported. "
                    f"Coverage: {coverage:.1%}."
                ),
            )
        except Exception as e:
            raise UnsupportedClaimError(
                f"Unsupported claim detection failed: {e}"
            ) from e

    def _assess_claim(
        self,
        claim: str,
        evidence: dict | None,
    ) -> UnsupportedClaim:
        keywords = self._extract_keywords(claim)

        if evidence is None or not evidence:
            return UnsupportedClaim(
                claim=claim,
                support_level=SupportLevel.UNSUPPORTED,
                confidence=0.9,
                matched_evidence=[],
                missing_evidence=keywords,
                details="No evidence provided to verify claim.",
            )

        matched: list[str] = []
        missing: list[str] = []
        contradictory: list[str] = []

        for keyword in keywords:
            found = False
            for ev_key in evidence:
                if keyword.lower() in ev_key.lower() or ev_key.lower() in keyword.lower():
                    ev_val = evidence[ev_key]
                    if isinstance(ev_val, str) and ev_val.lower() in (
                        "contradict", "contradictory", "false", "incorrect", "no",
                    ):
                        contradictory.append(ev_key)
                    else:
                        matched.append(ev_key)
                    found = True
                    break
            if not found:
                missing.append(keyword)

        if contradictory and not matched:
            return UnsupportedClaim(
                claim=claim,
                support_level=SupportLevel.CONTRADICTORY,
                confidence=0.85,
                matched_evidence=list(set(matched)),
                missing_evidence=missing,
                details="Evidence contradicts claim.",
            )

        if matched and not missing:
            relevance = len(matched) / max(len(keywords), 1)
            return UnsupportedClaim(
                claim=claim,
                support_level=SupportLevel.FULLY_SUPPORTED,
                confidence=min(1.0, relevance + 0.2),
                matched_evidence=list(set(matched)),
                missing_evidence=missing,
                details=f"Claim supported by {len(set(matched))} evidence references.",
            )

        if matched and missing:
            return UnsupportedClaim(
                claim=claim,
                support_level=SupportLevel.PARTIALLY_SUPPORTED,
                confidence=0.6,
                matched_evidence=list(set(matched)),
                missing_evidence=missing,
                details=(
                    f"Partially supported: {len(set(matched))} matched, "
                    f"{len(missing)} missing."
                ),
            )

        return UnsupportedClaim(
            claim=claim,
            support_level=SupportLevel.UNSUPPORTED,
            confidence=0.9,
            matched_evidence=[],
            missing_evidence=keywords,
            details="No evidence matched this claim.",
        )

    @staticmethod
    def _extract_keywords(claim: str) -> list[str]:
        words = re.findall(r'\b[a-zA-Z]{3,}\b', claim.lower())
        return [w for w in words if w not in DefaultUnsupportedClaimDetector.STOP_WORDS]
