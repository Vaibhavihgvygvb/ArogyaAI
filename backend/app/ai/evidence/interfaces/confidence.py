from abc import ABC, abstractmethod

from app.ai.evidence.schemas import (
    Citation,
    ConflictResult,
    CoverageResult,
    EvidenceState,
    ConfidenceResult,
    VerificationResult,
)


class ConfidenceCalculator(ABC):
    @abstractmethod
    async def calculate(
        self,
        verification_results: list[VerificationResult],
        coverage: CoverageResult | None = None,
        conflicts: list[ConflictResult] | None = None,
        citations: list[Citation] | None = None,
        state: EvidenceState | None = None,
    ) -> ConfidenceResult:
        ...
