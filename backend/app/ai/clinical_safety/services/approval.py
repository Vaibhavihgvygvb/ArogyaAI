from app.ai.clinical_safety.exceptions import SafetyApprovalError
from app.ai.clinical_safety.interfaces.approval import SafetyApprovalEngine
from app.ai.clinical_safety.schemas import (
    ApprovalDecision,
    ApprovalResult,
    ClinicalRiskReport,
    ComplianceReport,
    DisclaimerResult,
    EmergencyReport,
    HallucinationReport,
    RiskLevel,
    UnsupportedClaimReport,
)


class DefaultSafetyApprovalEngine(SafetyApprovalEngine):

    CRITICAL_HALLUCINATION_TYPES = frozenset({
        "fabricated_medication",
        "fabricated_disease",
    })

    def __init__(self, config=None):
        self.config = config

    async def approve(
        self,
        hallucination_report: HallucinationReport,
        unsupported_report: UnsupportedClaimReport,
        risk_report: ClinicalRiskReport,
        compliance_report: ComplianceReport,
        disclaimer_result: DisclaimerResult,
        emergency_report: EmergencyReport | None = None,
    ) -> ApprovalResult:
        try:
            reasons: list[str] = []
            warnings: list[str] = []
            requires_escalation = False
            requires_override = False

            has_critical_hallucinations = any(
                r.hallucination_type.value
                in self.CRITICAL_HALLUCINATION_TYPES
                and r.confidence > 0.8
                for r in hallucination_report.results
            )

            compliance_failed = {
                c.check_name
                for c in compliance_report.checks
                if not c.passed
            }

            reject_reasons: list[str] = []
            if hallucination_report.hallucination_rate > 0.3:
                reject_reasons.append(
                    f"High hallucination rate: "
                    f"{hallucination_report.hallucination_rate:.1%}"
                )
            if has_critical_hallucinations:
                reject_reasons.append(
                    "Critical hallucination detected "
                    "(high-confidence fabricated medication/disease)"
                )
            if "Hallucination Check" in compliance_failed:
                reject_reasons.append(
                    "Hallucination compliance check failed"
                )
            if "No Prohibited Claims" in compliance_failed:
                reject_reasons.append("Prohibited claims detected")

            if reject_reasons:
                return ApprovalResult(
                    decision=ApprovalDecision.REJECT,
                    reasons=reject_reasons,
                    warnings=[],
                    requires_escalation=True,
                    requires_override=True,
                    summary="Response rejected due to safety concerns.",
                )

            unsupported_rate = 0.0
            if unsupported_report.total_claims > 0:
                unsupported_rate = (
                    unsupported_report.unsupported_count
                    / unsupported_report.total_claims
                )

            escalation_reasons: list[str] = []
            if risk_report.overall_risk == RiskLevel.CRITICAL:
                escalation_reasons.append("Critical risk level")
            if emergency_report and emergency_report.requires_override:
                escalation_reasons.append(
                    "Emergency situation requires human override"
                )
            if unsupported_rate > 0.5:
                escalation_reasons.append(
                    f"High unsupported claim rate: {unsupported_rate:.1%}"
                )
            if len(compliance_failed) >= 2:
                escalation_reasons.append(
                    f"Multiple compliance checks failed: "
                    f"{', '.join(sorted(compliance_failed))}"
                )

            if escalation_reasons:
                return ApprovalResult(
                    decision=ApprovalDecision.ESCALATE,
                    reasons=escalation_reasons,
                    warnings=[],
                    requires_escalation=True,
                    requires_override=bool(
                        emergency_report
                        and emergency_report.requires_override
                    ),
                    summary="Response requires escalation due to concerns.",
                )

            warning_reasons: list[str] = []
            if risk_report.overall_risk == RiskLevel.HIGH:
                warning_reasons.append("High risk level")
            if (
                0.1
                < hallucination_report.hallucination_rate
                <= 0.3
            ):
                warning_reasons.append(
                    f"Moderate hallucination rate: "
                    f"{hallucination_report.hallucination_rate:.1%}"
                )
            for check_name in sorted(compliance_failed):
                warning_reasons.append(
                    f"Compliance warning: {check_name}"
                )

            if warning_reasons:
                return ApprovalResult(
                    decision=ApprovalDecision.APPROVED_WITH_WARNINGS,
                    reasons=[],
                    warnings=warning_reasons,
                    requires_escalation=False,
                    requires_override=False,
                    summary=(
                        f"Approved with {len(warning_reasons)} "
                        f"warning(s)."
                    ),
                )

            return ApprovalResult(
                decision=ApprovalDecision.APPROVED,
                reasons=["All safety checks passed."],
                warnings=[],
                requires_escalation=False,
                requires_override=False,
                summary=(
                    "Response approved. All safety checks passed."
                ),
            )
        except Exception as e:
            raise SafetyApprovalError(
                f"Safety approval failed: {e}"
            ) from e
