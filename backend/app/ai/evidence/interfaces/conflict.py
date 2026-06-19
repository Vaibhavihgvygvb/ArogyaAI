from abc import ABC, abstractmethod

from app.ai.evidence.schemas import ConflictResult, EvidenceState, VerificationResult


class ConflictDetector(ABC):
    @abstractmethod
    async def detect(
        self,
        verification_results: list[VerificationResult],
        state: EvidenceState | None = None,
    ) -> list[ConflictResult]:
        ...
