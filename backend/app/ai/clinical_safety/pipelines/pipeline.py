import time

from app.ai.clinical_safety.config import ClinicalSafetyConfig
from app.ai.clinical_safety.exceptions import SafetyPipelineError
from app.ai.clinical_safety.interfaces.approval import SafetyApprovalEngine
from app.ai.clinical_safety.interfaces.compliance import ComplianceValidator
from app.ai.clinical_safety.interfaces.disclaimer import DisclaimerEngine
from app.ai.clinical_safety.interfaces.emergency import EmergencyDetector
from app.ai.clinical_safety.interfaces.hallucination import HallucinationDetector
from app.ai.clinical_safety.interfaces.phi import PHIValidator
from app.ai.clinical_safety.interfaces.risk import ClinicalRiskEngine
from app.ai.clinical_safety.interfaces.unsupported import UnsupportedClaimDetector
from app.ai.clinical_safety.schemas import (
    PipelineResult,
    SafetyState,
)
from app.ai.clinical_safety.services.approval import DefaultSafetyApprovalEngine
from app.ai.clinical_safety.services.compliance import DefaultComplianceValidator
from app.ai.clinical_safety.services.disclaimer import DefaultDisclaimerEngine
from app.ai.clinical_safety.services.emergency import DefaultEmergencyDetector
from app.ai.clinical_safety.services.hallucination import DefaultHallucinationDetector
from app.ai.clinical_safety.services.phi import DefaultPHIValidator
from app.ai.clinical_safety.services.risk import DefaultClinicalRiskEngine
from app.ai.clinical_safety.services.unsupported import DefaultUnsupportedClaimDetector


class ClinicalSafetyPipeline:
    def __init__(
        self,
        hallucination_detector: HallucinationDetector | None = None,
        unsupported_detector: UnsupportedClaimDetector | None = None,
        risk_engine: ClinicalRiskEngine | None = None,
        emergency_detector: EmergencyDetector | None = None,
        phi_validator: PHIValidator | None = None,
        disclaimer_engine: DisclaimerEngine | None = None,
        compliance_validator: ComplianceValidator | None = None,
        approval_engine: SafetyApprovalEngine | None = None,
        config: ClinicalSafetyConfig | None = None,
    ):
        self._hallucination_detector = hallucination_detector or DefaultHallucinationDetector()
        self._unsupported_detector = unsupported_detector or DefaultUnsupportedClaimDetector()
        self._risk_engine = risk_engine or DefaultClinicalRiskEngine()
        self._emergency_detector = emergency_detector or DefaultEmergencyDetector()
        self._phi_validator = phi_validator or DefaultPHIValidator()
        self._disclaimer_engine = disclaimer_engine or DefaultDisclaimerEngine()
        self._compliance_validator = compliance_validator or DefaultComplianceValidator()
        self._approval_engine = approval_engine or DefaultSafetyApprovalEngine()
        self._config = config or ClinicalSafetyConfig()

    async def run(
        self,
        text: str,
        claims: list[str] | None = None,
        evidence: dict | None = None,
        config_override: dict | None = None,
    ) -> PipelineResult:
        start = time.time()
        steps_completed: list[str] = []
        steps_skipped: list[str] = []
        errors: list[str] = []

        state = SafetyState(response_text=text, config=config_override or {})

        try:
            resolved_claims = claims
            if not resolved_claims and text:
                resolved_claims = self._hallucination_detector._extract_claims(text)
            state.claims = resolved_claims or []

            hallu = await self._hallucination_detector.detect(text, state.claims, evidence)
            state.hallucination_report = hallu
            steps_completed.append("hallucination")

            emergency = await self._emergency_detector.detect(text, state.claims)
            state.emergency_report = emergency
            steps_completed.append("emergency")

            unsup = await self._unsupported_detector.detect(state.claims, evidence)
            state.unsupported_report = unsup
            steps_completed.append("unsupported_claims")

            risk = await self._risk_engine.assess(hallu, unsup, emergency)
            state.risk_report = risk
            steps_completed.append("risk_assessment")

            phi = await self._phi_validator.validate(text)
            state.phi_report = phi
            steps_completed.append("phi_validation")

            disc = await self._disclaimer_engine.select(risk, emergency, phi)
            state.disclaimer_result = disc
            steps_completed.append("disclaimer")

            comp = await self._compliance_validator.validate(hallu, unsup, disc, risk)
            state.compliance_report = comp
            steps_completed.append("compliance")

            approval = await self._approval_engine.approve(
                hallu, unsup, risk, comp, disc, emergency
            )
            state.approval_result = approval
            steps_completed.append("approval")
        except Exception as e:
            errors.append(f"Pipeline error: {e}")
            raise SafetyPipelineError(f"Pipeline execution failed: {e}")

        total_time = round((time.time() - start) * 1000, 2)

        return PipelineResult(
            state=state,
            pipeline_name="clinical_safety",
            total_processing_time_ms=total_time,
            steps_completed=steps_completed,
            steps_skipped=steps_skipped,
            errors=errors,
            success=len(errors) == 0,
        )
