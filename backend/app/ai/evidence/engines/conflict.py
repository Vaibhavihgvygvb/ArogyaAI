import re

from app.ai.evidence.interfaces.conflict import ConflictDetector
from app.ai.evidence.schemas import (
    ConflictResult,
    ConflictType,
    EvidenceState,
    VerificationResult,
    VerificationStatus,
)


_CONTRADICTION_PATTERNS: list[str] = [
    r"\b(contraindicated|do not use|avoid|harmful)\b",
    r"\b(no evidence|insufficient evidence|lacks evidence)\b",
    r"\b(not recommended|should not|must not|never)\b",
    r"\b(ineffective|unproven|unsubstantiated)\b",
]

_DIRECTIONAL_PATTERNS: list[str] = [
    r"\b(increase|decrease|raise|lower)\b",
    r"\b(improve|worsen|better|worse)\b",
    r"\b(may|might|could|possibly)\b",
]


class ConflictDetectorEngine(ConflictDetector):
    async def detect(
        self,
        verification_results: list[VerificationResult],
        state: EvidenceState | None = None,
    ) -> list[ConflictResult]:
        if not verification_results:
            return []

        conflicts: list[ConflictResult] = []
        for idx, vr in enumerate(verification_results):
            if not vr.contradicting_sources:
                continue
            conflict = self._analyze_conflict(vr, idx)
            if conflict:
                conflicts.append(conflict)

        for i in range(len(verification_results)):
            for j in range(i + 1, len(verification_results)):
                cross = self._detect_cross_claim_conflict(
                    verification_results[i], verification_results[j], i, j
                )
                if cross:
                    conflicts.append(cross)

        return conflicts

    def _analyze_conflict(
        self, vr: VerificationResult, idx: int
    ) -> ConflictResult | None:
        if not vr.contradicting_sources:
            return None

        text = vr.span.claim.lower()
        for pattern in _CONTRADICTION_PATTERNS:
            if re.search(pattern, text):
                return ConflictResult(
                    span_index=idx,
                    claim=vr.span.claim,
                    conflict_type=ConflictType.CONTRADICTORY,
                    sources=vr.contradicting_sources,
                    severity="high",
                    description=f"Contradictory evidence found for claim: {vr.span.claim}",
                    resolution="Review latest guidelines for definitive recommendation.",
                )

        for pattern in _DIRECTIONAL_PATTERNS:
            if re.search(pattern, text):
                return ConflictResult(
                    span_index=idx,
                    claim=vr.span.claim,
                    conflict_type=ConflictType.DIRECTIONAL,
                    sources=vr.supporting_sources + vr.contradicting_sources,
                    severity="medium",
                    description=f"Directional conflict in evidence for: {vr.span.claim}",
                    resolution="Consider effect size and confidence intervals.",
                )

        return ConflictResult(
            span_index=idx,
            claim=vr.span.claim,
            conflict_type=ConflictType.DIRECT,
            sources=vr.contradicting_sources,
            severity="medium",
            description=f"Direct conflict between sources for: {vr.span.claim}",
            resolution="Evaluate source quality and recency.",
        )

    def _detect_cross_claim_conflict(
        self,
        vr1: VerificationResult,
        vr2: VerificationResult,
        idx1: int,
        idx2: int,
    ) -> ConflictResult | None:
        claim1 = set(vr1.span.claim.lower().split())
        claim2 = set(vr2.span.claim.lower().split())
        overlap = claim1 & claim2
        if not overlap:
            return None

        v1 = vr1.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED)
        v2 = vr2.status in (VerificationStatus.VERIFIED, VerificationStatus.PARTIALLY_VERIFIED)
        if v1 != v2:
            return ConflictResult(
                span_index=idx1,
                claim=vr1.span.claim,
                conflict_type=ConflictType.DIRECTIONAL,
                sources=vr1.supporting_sources + vr2.supporting_sources,
                severity="low",
                description=f"Cross-claim conflict detected between claims {idx1 + 1} and {idx2 + 1}",
                resolution="Verify both claims independently.",
            )
        return None
