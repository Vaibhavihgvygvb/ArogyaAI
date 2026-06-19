from abc import ABC, abstractmethod

from app.ai.clinical_safety.schemas import EmergencyReport


class EmergencyDetector(ABC):
    @abstractmethod
    async def detect(
        self,
        text: str,
        claims: list[str],
    ) -> EmergencyReport:
        ...
