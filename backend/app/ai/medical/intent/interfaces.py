from abc import ABC, abstractmethod

from app.ai.medical.engine.schemas import IntentResult


class IntentClassifierABC(ABC):
    @abstractmethod
    async def classify(self, query: str) -> IntentResult:
        ...


class IntentServiceABC(ABC):
    @abstractmethod
    async def detect(self, query: str, specialty_hint: str | None = None) -> IntentResult:
        ...
