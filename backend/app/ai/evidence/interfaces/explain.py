from abc import ABC, abstractmethod

from app.ai.evidence.schemas import (
    Citation,
    ConflictResult,
    ConfidenceResult,
    CoverageResult,
    EvidenceState,
    ExplanationResult,
    VerificationResult,
)


class ExplainabilityProvider(ABC):
    @abstractmethod
    async def explain(
        self,
        verification_results: list[VerificationResult],
        coverage: CoverageResult | None = None,
        conflicts: list[ConflictResult] | None = None,
        confidence: ConfidenceResult | None = None,
        citations: list[Citation] | None = None,
        state: EvidenceState | None = None,
    ) -> ExplanationResult:
        ...
