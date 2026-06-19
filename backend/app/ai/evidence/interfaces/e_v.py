from abc import ABC, abstractmethod

from app.ai.evidence.schemas import EvidenceSpan, EvidenceState, VerificationResult


class EvidenceVerifier(ABC):
    @abstractmethod
    async def verify(
        self, spans: list[EvidenceSpan], state: EvidenceState | None = None
    ) -> list[VerificationResult]:
        ...
