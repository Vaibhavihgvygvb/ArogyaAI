import re

from app.ai.clinical_safety.exceptions import DisclaimerError
from app.ai.clinical_safety.interfaces.disclaimer import DisclaimerEngine
from app.ai.clinical_safety.schemas import (
    ClinicalRiskReport,
    DisclaimerConfig,
    DisclaimerResult,
    DisclaimerType,
    EmergencyReport,
    PHIValidationReport,
    RiskLevel,
)


class DefaultDisclaimerEngine(DisclaimerEngine):

    DISCLAIMERS: dict[DisclaimerType, DisclaimerConfig] = {
        DisclaimerType.GENERAL_MEDICAL: DisclaimerConfig(
            disclaimer_type=DisclaimerType.GENERAL_MEDICAL,
            text="This information is for educational purposes only and does not constitute medical advice.",
            severity="informational",
            required=True,
            use_emergency_override=False,
        ),
        DisclaimerType.EMERGENCY: DisclaimerConfig(
            disclaimer_type=DisclaimerType.EMERGENCY,
            text="This is an emergency situation. Please call emergency services immediately. Do not rely on AI advice in an emergency.",
            severity="high",
            required=True,
            use_emergency_override=True,
        ),
        DisclaimerType.MEDICATION: DisclaimerConfig(
            disclaimer_type=DisclaimerType.MEDICATION,
            text="Medication information provided is for reference only. Consult your doctor or pharmacist before taking any medication.",
            severity="medium",
            required=True,
            use_emergency_override=False,
        ),
        DisclaimerType.MENTAL_HEALTH: DisclaimerConfig(
            disclaimer_type=DisclaimerType.MENTAL_HEALTH,
            text="Mental health information is sensitive. Please consult a qualified mental health professional.",
            severity="medium",
            required=True,
            use_emergency_override=False,
        ),
        DisclaimerType.PREGNANCY: DisclaimerConfig(
            disclaimer_type=DisclaimerType.PREGNANCY,
            text="Pregnancy-related information should always be discussed with your obstetrician or midwife.",
            severity="medium",
            required=True,
            use_emergency_override=False,
        ),
        DisclaimerType.PEDIATRIC: DisclaimerConfig(
            disclaimer_type=DisclaimerType.PEDIATRIC,
            text="Pediatric medical information should always be verified with a pediatrician.",
            severity="medium",
            required=True,
            use_emergency_override=False,
        ),
        DisclaimerType.CLINICAL_UNCERTAINTY: DisclaimerConfig(
            disclaimer_type=DisclaimerType.CLINICAL_UNCERTAINTY,
            text="There is uncertainty in this medical information. Please consult a healthcare professional.",
            severity="medium",
            required=True,
            use_emergency_override=False,
        ),
    }

    MEDICATION_RE = re.compile(
        r'\b(?:medication|drug|prescription|dosage|dose|tablet|capsule|'
        r'medicine|pharmaceutical)\b',
        re.IGNORECASE,
    )
    MENTAL_HEALTH_RE = re.compile(
        r'\b(?:mental\s+health|depression|anxiety|psychiatric|therapy|'
        r'counseling|psychological|bipolar|schizophrenia|ptsd|ocd)\b',
        re.IGNORECASE,
    )
    PREGNANCY_RE = re.compile(
        r'\b(?:pregnancy|pregnant|prenatal|antenatal|obstetric|fetus|fetal|'
        r'breastfeeding|lactation|maternity)\b',
        re.IGNORECASE,
    )
    PEDIATRIC_RE = re.compile(
        r'\b(?:pediatric|child|infant|newborn|toddler|adolescent|children|baby|'
        r'neonatal)\b',
        re.IGNORECASE,
    )

    def __init__(self, config=None):
        self.config = config

    async def select(
        self,
        risk_report: ClinicalRiskReport | None,
        emergency_report: EmergencyReport | None,
        phi_report: PHIValidationReport | None = None,
    ) -> DisclaimerResult:
        try:
            selected: list[DisclaimerConfig] = [
                self.DISCLAIMERS[DisclaimerType.GENERAL_MEDICAL]
            ]
            has_emergency_disclaimer = False
            has_medication_disclaimer = False
            has_mental_health_disclaimer = False

            if emergency_report and emergency_report.has_emergency:
                selected.append(self.DISCLAIMERS[DisclaimerType.EMERGENCY])
                has_emergency_disclaimer = True

            if risk_report and risk_report.overall_risk in (
                RiskLevel.HIGH, RiskLevel.CRITICAL,
            ):
                unc = self.DISCLAIMERS[DisclaimerType.CLINICAL_UNCERTAINTY]
                if unc not in selected:
                    selected.append(unc)

            context = self._extract_context(
                risk_report, emergency_report, phi_report
            )

            if self.MEDICATION_RE.search(context):
                med = self.DISCLAIMERS[DisclaimerType.MEDICATION]
                if med not in selected:
                    selected.append(med)
                    has_medication_disclaimer = True

            if self.MENTAL_HEALTH_RE.search(context):
                mh = self.DISCLAIMERS[DisclaimerType.MENTAL_HEALTH]
                if mh not in selected:
                    selected.append(mh)
                    has_mental_health_disclaimer = True

            if self.PREGNANCY_RE.search(context):
                preg = self.DISCLAIMERS[DisclaimerType.PREGNANCY]
                if preg not in selected:
                    selected.append(preg)

            if self.PEDIATRIC_RE.search(context):
                peds = self.DISCLAIMERS[DisclaimerType.PEDIATRIC]
                if peds not in selected:
                    selected.append(peds)

            return DisclaimerResult(
                selected_disclaimers=selected,
                has_emergency_disclaimer=has_emergency_disclaimer,
                has_medication_disclaimer=has_medication_disclaimer,
                has_mental_health_disclaimer=has_mental_health_disclaimer,
                summary=f"Selected {len(selected)} disclaimer(s).",
            )
        except Exception as e:
            raise DisclaimerError(
                f"Disclaimer selection failed: {e}"
            ) from e

    async def get_disclaimers(self) -> list[DisclaimerConfig]:
        return list(self.DISCLAIMERS.values())

    @staticmethod
    def _extract_context(
        risk_report: ClinicalRiskReport | None,
        emergency_report: EmergencyReport | None,
        phi_report: PHIValidationReport | None,
    ) -> str:
        parts: list[str] = []
        if risk_report:
            for r in risk_report.results:
                parts.extend(r.emergency_indicators)
                parts.extend(r.factors)
        if emergency_report:
            for r in emergency_report.results:
                parts.append(str(r.emergency_type.value))
                parts.extend(r.indicators)
        if phi_report:
            for f in phi_report.findings:
                parts.append(f.phi_type.value)
                parts.append(f.value_preview)
        return " ".join(parts)
