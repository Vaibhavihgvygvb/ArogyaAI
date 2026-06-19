from abc import ABC, abstractmethod

from app.ai.clinical_safety.schemas import (
    ApprovalResult,
    ClinicalRiskReport,
    ComplianceReport,
    DisclaimerResult,
    EmergencyReport,
    HallucinationReport,
    UnsupportedClaimReport,
)


class SafetyApprovalEngine(ABC):
    @abstractmethod
    async def approve(
        self,
        hallucination_report: HallucinationReport,
        unsupported_report: UnsupportedClaimReport,
        risk_report: ClinicalRiskReport,
        compliance_report: ComplianceReport,
        disclaimer_result: DisclaimerResult,
        emergency_report: EmergencyReport | None = None,
    ) -> ApprovalResult:
        ...
