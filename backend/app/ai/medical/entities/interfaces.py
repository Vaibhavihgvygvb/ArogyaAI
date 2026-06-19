from abc import ABC, abstractmethod

from app.ai.medical.engine.schemas import EntityResult


class EntityExtractorABC(ABC):
    @abstractmethod
    def extract(self, query: str) -> EntityResult:
        ...
