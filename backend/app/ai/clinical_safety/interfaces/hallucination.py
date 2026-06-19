from abc import ABC, abstractmethod

from app.ai.clinical_safety.schemas import HallucinationReport


class HallucinationDetector(ABC):
    @abstractmethod
    async def detect(
        self,
        text: str,
        claims: list[str],
        evidence: dict | None = None,
    ) -> HallucinationReport:
        ...
