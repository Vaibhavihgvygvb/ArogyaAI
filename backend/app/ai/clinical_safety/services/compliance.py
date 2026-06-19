import re

from app.ai.clinical_safety.exceptions import ComplianceError
from app.ai.clinical_safety.interfaces.compliance import ComplianceValidator
from app.ai.clinical_safety.schemas import (
    ClinicalRiskReport,
    ComplianceCheck,
    ComplianceReport,
    DisclaimerResult,
    HallucinationReport,
    UnsupportedClaimReport,
)


class DefaultComplianceValidator(ComplianceValidator):

    GUARANTEE_RE = re.compile(
        r'\b(definitely|absolutely|guaranteed|100%\s*effective|'
        r'completely\s+safe)\b',
        re.IGNORECASE,
    )

    def __init__(self, config=None):
        self.config = config

    async def validate(
        self,
        hallucination_report: HallucinationReport,
        unsupported_report: UnsupportedClaimReport,
        disclaimer_result: DisclaimerResult,
        risk_report: ClinicalRiskReport | None = None,
    ) -> ComplianceReport:
        try:
            checks: list[ComplianceCheck] = []

            checks.append(self._check_hallucination(hallucination_report))
            checks.append(self._check_unsupported(unsupported_report))
            checks.append(self._check_evidence_threshold(unsupported_report))
            checks.append(self._check_disclaimer(disclaimer_result))
            checks.append(
                self._check_prohibited_claims(hallucination_report)
            )
            checks.append(
                self._check_absolute_guarantees(hallucination_report)
            )
            checks.append(
                self._check_citation_coverage(hallucination_report)
            )

            total = len(checks)
            passed_count = sum(1 for c in checks if c.passed)
            failed_count = total - passed_count

            return ComplianceReport(
                checks=checks,
                total_checks=total,
                passed_checks=passed_count,
                failed_checks=failed_count,
                passed=failed_count == 0,
                summary=f"{passed_count}/{total} checks passed.",
            )
        except Exception as e:
            raise ComplianceError(
                f"Compliance validation failed: {e}"
            ) from e

    def _check_hallucination(
        self,
        report: HallucinationReport,
    ) -> ComplianceCheck:
        return ComplianceCheck(
            check_name="Hallucination Check",
            passed=report.passed,
            severity="high",
            details=(
                f"Hallucination rate: {report.hallucination_rate:.1%}."
            ),
        )

    def _check_unsupported(
        self,
        report: UnsupportedClaimReport,
    ) -> ComplianceCheck:
        unsupported_passed = (
            report.passed or report.coverage_score >= 0.3
        )
        return ComplianceCheck(
            check_name="Unsupported Claims Check",
            passed=unsupported_passed,
            severity="high",
            details=(
                f"Coverage score: {report.coverage_score:.1%}."
            ),
        )

    def _check_evidence_threshold(
        self,
        report: UnsupportedClaimReport,
    ) -> ComplianceCheck:
        min_evidence = (
            getattr(self.config, 'CLINICAL_SAFETY_MIN_EVIDENCE_SCORE', 0.3)
            if self.config else 0.3
        )
        return ComplianceCheck(
            check_name="Evidence Threshold",
            passed=report.coverage_score >= min_evidence,
            severity="medium",
            details=(
                f"Evidence coverage: {report.coverage_score:.1%} "
                f"(minimum: {min_evidence:.0%})."
            ),
        )

    @staticmethod
    def _check_disclaimer(
        result: DisclaimerResult,
    ) -> ComplianceCheck:
        has_general = any(
            d.disclaimer_type.value == "general_medical"
            for d in result.selected_disclaimers
        )
        return ComplianceCheck(
            check_name="Disclaimer Present",
            passed=has_general,
            severity="high",
            details=(
                "General medical disclaimer present."
                if has_general
                else "Missing general medical disclaimer."
            ),
        )

    def _check_prohibited_claims(
        self,
        report: HallucinationReport,
    ) -> ComplianceCheck:
        terms_str = (
            getattr(self.config, 'CLINICAL_SAFETY_PROHIBITED_TERMS',
                    "guarantee,cure,100%,miracle,secret")
            if self.config
            else "guarantee,cure,100%,miracle,secret"
        )
        prohibited = [t.strip().lower() for t in terms_str.split(",")]
        found: list[str] = []
        for result in report.results:
            claim_lower = result.claim.lower()
            for term in prohibited:
                if term in claim_lower and term not in found:
                    found.append(term)
        return ComplianceCheck(
            check_name="No Prohibited Claims",
            passed=len(found) == 0,
            severity="high",
            details=(
                f"Prohibited terms found: {', '.join(found)}."
                if found
                else "No prohibited terms detected."
            ),
        )

    @staticmethod
    def _check_absolute_guarantees(
        report: HallucinationReport,
    ) -> ComplianceCheck:
        found: list[str] = []
        for result in report.results:
            matches = DefaultComplianceValidator.GUARANTEE_RE.findall(
                result.claim
            )
            for m in matches:
                if m not in found:
                    found.append(m)
        return ComplianceCheck(
            check_name="No Absolute Guarantees",
            passed=len(found) == 0,
            severity="medium",
            details=(
                f"Absolute guarantees found: {', '.join(found)}."
                if found
                else "No absolute guarantees detected."
            ),
        )

    @staticmethod
    def _check_citation_coverage(
        report: HallucinationReport,
    ) -> ComplianceCheck:
        citation_flagged = any(
            r.hallucination_type.value == "fabricated_citation"
            for r in report.results
        )
        return ComplianceCheck(
            check_name="Citation Coverage",
            passed=not citation_flagged,
            severity="medium",
            details=(
                "Citations verified."
                if not citation_flagged
                else "Unverifiable citations detected."
            ),
        )
