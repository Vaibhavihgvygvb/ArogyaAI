from abc import ABC, abstractmethod

from app.ai.medical.engine.schemas import QueryUnderstandingResult


class QueryUnderstandingEngineABC(ABC):
    @abstractmethod
    async def analyze(self, query: str, conversation_id: str | None = None) -> QueryUnderstandingResult:
        ...

    @abstractmethod
    async def detect_intent(self, query: str) -> "IntentResult":
        ...

    @abstractmethod
    async def extract_entities(self, query: str) -> "EntityResult":
        ...

    @abstractmethod
    async def classify_specialty(self, query: str) -> "SpecialtyResult":
        ...

    @abstractmethod
    async def classify_urgency(self, query: str) -> "UrgencyResult":
        ...

    @abstractmethod
    async def classify_audience(self, query: str) -> "AudienceResult":
        ...

    @abstractmethod
    async def detect_language(self, query: str) -> "LanguageResult":
        ...

    @abstractmethod
    async def rewrite_query(self, query: str, conversation_id: str | None = None) -> "RewriteResult":
        ...
