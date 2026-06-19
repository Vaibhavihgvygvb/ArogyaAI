from abc import ABC, abstractmethod

from app.ai.clinical_safety.schemas import (
    ClinicalRiskReport,
    ComplianceReport,
    DisclaimerResult,
    HallucinationReport,
    UnsupportedClaimReport,
)


class ComplianceValidator(ABC):
    @abstractmethod
    async def validate(
        self,
        hallucination_report: HallucinationReport,
        unsupported_report: UnsupportedClaimReport,
        disclaimer_result: DisclaimerResult,
        risk_report: ClinicalRiskReport | None = None,
    ) -> ComplianceReport:
        ...
