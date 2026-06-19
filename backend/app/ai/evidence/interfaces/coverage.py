from abc import ABC, abstractmethod

from app.ai.evidence.schemas import CoverageResult, EvidenceState, VerificationResult


class CoverageAnalyzer(ABC):
    @abstractmethod
    async def analyze(
        self,
        verification_results: list[VerificationResult],
        state: EvidenceState | None = None,
    ) -> CoverageResult:
        ...
