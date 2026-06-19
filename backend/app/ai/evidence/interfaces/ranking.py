from abc import ABC, abstractmethod

from app.ai.evidence.schemas import EvidenceState, VerifiedSource


class SourceRankingProvider(ABC):
    @abstractmethod
    async def rank(
        self,
        sources: list[VerifiedSource],
        state: EvidenceState | None = None,
    ) -> list[VerifiedSource]:
        ...
