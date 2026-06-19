from abc import ABC, abstractmethod

from app.ai.clinical_safety.schemas import (
    ClinicalRiskReport,
    EmergencyReport,
    HallucinationReport,
    UnsupportedClaimReport,
)


class ClinicalRiskEngine(ABC):
    @abstractmethod
    async def assess(
        self,
        hallucination_report: HallucinationReport | None,
        unsupported_report: UnsupportedClaimReport | None,
        emergency_report: EmergencyReport | None = None,
    ) -> ClinicalRiskReport:
        ...
