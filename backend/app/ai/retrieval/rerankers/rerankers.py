import time

from app.ai.retrieval.interfaces.interfaces import RerankerProvider
from app.ai.retrieval.schemas.schemas import RetrievalResult


class NoOpReranker(RerankerProvider):
    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        ranked = []
        for i, r in enumerate(results):
            r.rank = i + 1
            ranked.append(r)
        if top_k is not None:
            ranked = ranked[:top_k]
        return ranked


class MockReranker(RerankerProvider):
    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        ranked = sorted(results, key=lambda r: r.score, reverse=True)
        for i, r in enumerate(ranked):
            r.rank = i + 1
        if top_k is not None:
            ranked = ranked[:top_k]
        return ranked


class TimeReranker(RerankerProvider):
    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        ranked = sorted(
            results,
            key=lambda r: (
                r.metadata.get("created_at", "") if isinstance(r.metadata, dict) else ""
            ),
            reverse=True,
        )
        for i, r in enumerate(ranked):
            r.rank = i + 1
        if top_k is not None:
            ranked = ranked[:top_k]
        return ranked
