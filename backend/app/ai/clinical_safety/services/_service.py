import time

from app.ai.clinical_safety.exceptions import ClinicalSafetyError, SafetyPipelineError
from app.ai.clinical_safety.pipelines.pipeline import ClinicalSafetyPipeline
from app.ai.clinical_safety.schemas import (
    ApprovalResult,
    ClinicalRiskReport,
    ComplianceReport,
    DisclaimerResult,
    EmergencyReport,
    HallucinationReport,
    PHIValidationReport,
    PipelineResult,
    SafetyServiceResult,
    UnsupportedClaimReport,
)


class ClinicalSafetyService:
    def __init__(
        self,
        pipeline: ClinicalSafetyPipeline | None = None,
    ):
        from app.ai.clinical_safety.pipelines.pipeline import ClinicalSafetyPipeline
        self._pipeline = pipeline or ClinicalSafetyPipeline()

    async def validate(
        self,
        response_text: str,
        claims: list[str] | None = None,
        evidence: dict | None = None,
    ) -> SafetyServiceResult:
        start = time.time()
        warnings: list[str] = []
        errors: list[str] = []

        if not response_text or not response_text.strip():
            return SafetyServiceResult(
                passed=False,
                pipeline_result=None,
                summary="No response text provided.",
                warnings=[],
                errors=["Empty response text"],
                processing_time_ms=0.0,
            )

        try:
            pipeline_result = await self._pipeline.run(
                text=response_text, claims=claims, evidence=evidence,
            )
        except SafetyPipelineError as e:
            return SafetyServiceResult(
                passed=False,
                summary="Pipeline execution failed.",
                warnings=[],
                errors=[str(e)],
                processing_time_ms=round((time.time() - start) * 1000, 2),
            )
        except Exception as e:
            return SafetyServiceResult(
                passed=False,
                summary="Unexpected error during validation.",
                warnings=[],
                errors=[f"Validation error: {e}"],
                processing_time_ms=round((time.time() - start) * 1000, 2),
            )

        elapsed = round((time.time() - start) * 1000, 2)
        state = pipeline_result.state

        passed = pipeline_result.success
        approval = state.approval_result
        if approval:
            passed = approval.decision.value in ("approved", "approved_with_warnings")

        if pipeline_result.errors:
            errors.extend(pipeline_result.errors)

        if state.emergency_report and state.emergency_report.has_emergency:
            warnings.append(f"Emergency detected: {state.emergency_report.max_severity}")

        if state.phi_report and state.phi_report.has_phi:
            warnings.append(f"PHI detected: {state.phi_report.total_findings} finding(s)")

        if approval and approval.warnings:
            warnings.extend(approval.warnings)

        if not passed and not errors:
            warnings.append("Validation completed with concerns.")

        state_summary = (
            f"Hallucination rate: {state.hallucination_report.hallucination_rate:.1%}, "
            f"Risk: {state.risk_report.overall_risk.value if state.risk_report else 'none'}"
        ) if state.hallucination_report and state.risk_report else "Validation complete."

        return SafetyServiceResult(
            passed=passed,
            pipeline_result=pipeline_result,
            approval=approval,
            summary=state_summary,
            warnings=warnings,
            errors=errors,
            processing_time_ms=elapsed,
        )

    async def detect_hallucinations(
        self,
        text: str,
        claims: list[str] | None = None,
        evidence: dict | None = None,
    ) -> HallucinationReport:
        result = await self._pipeline.run(text=text, claims=claims, evidence=evidence)
        return result.state.hallucination_report or HallucinationReport()

    async def detect_unsupported_claims(
        self,
        claims: list[str],
        evidence: dict | None = None,
    ) -> UnsupportedClaimReport:
        result = await self._pipeline.run(text="", claims=claims, evidence=evidence)
        return result.state.unsupported_report or UnsupportedClaimReport()

    async def assess_risk(
        self,
        text: str,
        claims: list[str] | None = None,
        evidence: dict | None = None,
    ) -> ClinicalRiskReport:
        result = await self._pipeline.run(text=text, claims=claims, evidence=evidence)
        return result.state.risk_report or ClinicalRiskReport()

    async def detect_emergency(
        self,
        text: str,
        claims: list[str] | None = None,
    ) -> EmergencyReport:
        result = await self._pipeline.run(text=text, claims=claims)
        return result.state.emergency_report or EmergencyReport()

    async def validate_phi(
        self,
        text: str,
    ) -> PHIValidationReport:
        result = await self._pipeline.run(text=text)
        return result.state.phi_report or PHIValidationReport()

    async def select_disclaimer(
        self,
        text: str,
        claims: list[str] | None = None,
        evidence: dict | None = None,
    ) -> DisclaimerResult:
        result = await self._pipeline.run(text=text, claims=claims, evidence=evidence)
        return result.state.disclaimer_result or DisclaimerResult()

    async def validate_compliance(
        self,
        text: str,
        claims: list[str] | None = None,
        evidence: dict | None = None,
    ) -> ComplianceReport:
        result = await self._pipeline.run(text=text, claims=claims, evidence=evidence)
        return result.state.compliance_report or ComplianceReport()

    async def get_approval(
        self,
        text: str,
        claims: list[str] | None = None,
        evidence: dict | None = None,
    ) -> ApprovalResult:
        result = await self._pipeline.run(text=text, claims=claims, evidence=evidence)
        return result.state.approval_result or ApprovalResult(
            decision="approved",
            reasons=["No approval decision available."],
        )
