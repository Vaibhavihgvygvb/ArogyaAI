import re

from app.ai.clinical_safety.exceptions import ClinicalRiskError
from app.ai.clinical_safety.interfaces.risk import ClinicalRiskEngine
from app.ai.clinical_safety.schemas import (
    ClinicalRiskReport,
    ClinicalRiskResult,
    EmergencyReport,
    HallucinationReport,
    RiskLevel,
    UnsupportedClaimReport,
)


class DefaultClinicalRiskEngine(ClinicalRiskEngine):

    SENSITIVE_TOPICS_RE = re.compile(
        r'\b(cancer|heart(?:\s+disease|\s+attack)?|stroke|suicide|overdose|'
        r'tumor|malignant|metastasis|cardiac|arrest|infarction|'
        r'hemorrhage|seizure|paralysis|coma)\b',
        re.IGNORECASE,
    )

    def __init__(self, config=None):
        self.config = config

    async def assess(
        self,
        hallucination_report: HallucinationReport | None,
        unsupported_report: UnsupportedClaimReport | None,
        emergency_report: EmergencyReport | None = None,
    ) -> ClinicalRiskReport:
        try:
            hallu_rate = (
                hallucination_report.hallucination_rate
                if hallucination_report else 0.0
            )
            unsupported_rate = 0.0
            if unsupported_report and unsupported_report.total_claims > 0:
                unsupported_rate = (
                    unsupported_report.unsupported_count
                    / unsupported_report.total_claims
                )

            hallu_impact = min(1.0, hallu_rate * 1.5) if hallu_rate > 0 else 0.0
            unsup_impact = min(1.0, unsupported_rate)

            text = self._reconstruct_text(
                hallucination_report, unsupported_report, emergency_report
            )
            topic_matches = self.SENSITIVE_TOPICS_RE.findall(text)
            topic_sensitivity = min(1.0, len(topic_matches) * 0.15)

            emergency_indicators: list[str] = []
            if emergency_report and emergency_report.has_emergency:
                for result in emergency_report.results:
                    if result.is_emergency:
                        emergency_indicators.extend(result.indicators)

            emergency_impact = min(1.0, len(emergency_indicators) * 0.2)

            overall = (
                hallu_impact * 0.30
                + unsup_impact * 0.25
                + topic_sensitivity * 0.20
                + emergency_impact * 0.25
            )
            overall = min(1.0, max(0.0, overall))

            factors: list[str] = []
            if hallu_impact > 0.2:
                factors.append(f"Hallucination rate: {hallu_rate:.1%}")
            if unsup_impact > 0.2:
                factors.append(f"Unsupported rate: {unsupported_rate:.1%}")
            if topic_sensitivity > 0.2:
                unique_topics = list(set(topic_matches))[:3]
                factors.append(
                    f"Sensitive topics: {', '.join(unique_topics)}"
                )
            if emergency_impact > 0.2:
                factors.append(
                    f"Emergency indicators: {len(emergency_indicators)} detected"
                )

            results = [
                ClinicalRiskResult(
                    risk_level=self._classify(overall),
                    score=overall,
                    factors=factors,
                    confidence_impact=hallu_impact,
                    unsupported_impact=unsup_impact,
                    topic_sensitivity=topic_sensitivity,
                    emergency_indicators=emergency_indicators,
                    details=f"Risk assessed with {len(factors)} contributing factor(s).",
                )
            ]

            overall_risk = self._classify(overall)
            return ClinicalRiskReport(
                results=results,
                overall_risk=overall_risk,
                max_risk_score=overall,
                passed=overall_risk in (RiskLevel.LOW, RiskLevel.MODERATE),
                summary=f"Clinical risk: {overall_risk.value} (score: {overall:.2f}).",
            )
        except Exception as e:
            raise ClinicalRiskError(f"Risk assessment failed: {e}") from e

    @staticmethod
    def _reconstruct_text(
        hallucination_report: HallucinationReport | None,
        unsupported_report: UnsupportedClaimReport | None,
        emergency_report: EmergencyReport | None,
    ) -> str:
        text_parts: list[str] = []
        if hallucination_report:
            text_parts.extend(r.claim for r in hallucination_report.results)
        if unsupported_report:
            text_parts.extend(c.claim for c in unsupported_report.claims)
        if emergency_report:
            for r in emergency_report.results:
                if r.indicators:
                    text_parts.extend(r.indicators)
        return " ".join(text_parts)

    @staticmethod
    def _classify(score: float) -> RiskLevel:
        if score < 0.25:
            return RiskLevel.LOW
        if score < 0.5:
            return RiskLevel.MODERATE
        if score < 0.75:
            return RiskLevel.HIGH
        return RiskLevel.CRITICAL
