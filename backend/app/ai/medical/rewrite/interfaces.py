from abc import ABC, abstractmethod

from app.ai.medical.engine.schemas import RewriteResult


class QueryRewriterABC(ABC):
    @abstractmethod
    async def rewrite(self, query: str) -> RewriteResult:
        ...
