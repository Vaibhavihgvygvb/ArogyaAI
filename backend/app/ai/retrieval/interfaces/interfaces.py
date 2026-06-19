from abc import ABC, abstractmethod

from app.ai.retrieval.schemas.schemas import RetrievalResult


class RerankerProvider(ABC):
    @abstractmethod
    async def rerank(
        self,
        query: str,
        results: list[RetrievalResult],
        top_k: int | None = None,
    ) -> list[RetrievalResult]:
        ...
