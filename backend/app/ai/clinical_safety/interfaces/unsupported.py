from abc import ABC, abstractmethod

from app.ai.clinical_safety.schemas import UnsupportedClaimReport


class UnsupportedClaimDetector(ABC):
    @abstractmethod
    async def detect(
        self,
        claims: list[str],
        evidence: dict | None = None,
    ) -> UnsupportedClaimReport:
        ...
