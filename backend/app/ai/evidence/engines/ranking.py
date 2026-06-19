from app.ai.evidence.interfaces.ranking import SourceRankingProvider
from app.ai.evidence.schemas import EvidenceState, VerifiedSource


class SourceRankingEngine(SourceRankingProvider):
    AUTHORITY_WEIGHT = 0.3
    RELEVANCE_WEIGHT = 0.4
    RECENCY_WEIGHT = 0.15
    QUALITY_WEIGHT = 0.15

    async def rank(
        self,
        sources: list[VerifiedSource],
        state: EvidenceState | None = None,
    ) -> list[VerifiedSource]:
        if not sources:
            return []

        scored = []
        for s in sources:
            score = (
                self.AUTHORITY_WEIGHT * s.authority_score
                + self.RELEVANCE_WEIGHT * s.relevance_score
                + self.RECENCY_WEIGHT * s.recency_score
                + self.QUALITY_WEIGHT * s.quality_score
            )
            scored.append((score, s))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored]
