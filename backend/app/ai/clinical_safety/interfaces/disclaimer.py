from abc import ABC, abstractmethod

from app.ai.clinical_safety.schemas import (
    ClinicalRiskReport,
    DisclaimerConfig,
    DisclaimerResult,
    EmergencyReport,
    PHIValidationReport,
)


class DisclaimerEngine(ABC):
    @abstractmethod
    async def select(
        self,
        risk_report: ClinicalRiskReport | None,
        emergency_report: EmergencyReport | None,
        phi_report: PHIValidationReport | None = None,
    ) -> DisclaimerResult:
        ...

    @abstractmethod
    async def get_disclaimers(self) -> list[DisclaimerConfig]:
        ...
