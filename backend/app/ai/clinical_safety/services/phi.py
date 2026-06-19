import re

from app.ai.clinical_safety.exceptions import PHIValidationError
from app.ai.clinical_safety.interfaces.phi import PHIValidator
from app.ai.clinical_safety.schemas import (
    PHIFinding,
    PHIValidationReport,
    PHIType,
)


class DefaultPHIValidator(PHIValidator):

    PATTERNS: dict[PHIType, tuple[re.Pattern, str]] = {
        PHIType.SSN: (
            re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            "high",
        ),
        PHIType.EMAIL: (
            re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'),
            "medium",
        ),
        PHIType.PHONE: (
            re.compile(r'\b(?:\+?91|0)?[6-9]\d{9}\b'),
            "high",
        ),
        PHIType.AADHAAR: (
            re.compile(r'\b\d{4}\s?\d{4}\s?\d{4}\b'),
            "high",
        ),
        PHIType.PASSPORT: (
            re.compile(r'\b[A-Z]{1,2}\d{6,8}\b'),
            "high",
        ),
        PHIType.CREDIT_CARD: (
            re.compile(r'\b\d{16}\b'),
            "high",
        ),
        PHIType.MEDICAL_RECORD_NUMBER: (
            re.compile(
                r'\b(?:MRN|MR#|medical\s+record\s*(?:number|#|id)|'
                r'chart\s*(?:number|#)|patient\s+id)\s*:?\s*'
                r'[A-Za-z0-9-]{4,}\b',
                re.IGNORECASE,
            ),
            "medium",
        ),
        PHIType.INSURANCE_ID: (
            re.compile(
                r'\b(?:INS-|POLICY-|POL-|MEMBER\s+ID|GROUP\s*#?|'
                r'SUBSCRIBER\s+ID)\s*:?\s*[A-Za-z0-9-]{4,}\b',
                re.IGNORECASE,
            ),
            "medium",
        ),
        PHIType.DOB: (
            re.compile(
                r'\b(?:DOB|date\s+of\s+birth|birth\s+date|born\s+on)\s*:?\s*'
                r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b',
                re.IGNORECASE,
            ),
            "medium",
        ),
        PHIType.PATIENT_NAME: (
            re.compile(
                r'\b(?:patient\s+(?:name|is|called)\s+'
                r'[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})',
            ),
            "low",
        ),
    }

    def __init__(self, config=None):
        self.config = config

    async def validate(self, text: str) -> PHIValidationReport:
        try:
            findings: list[PHIFinding] = []

            for phi_type, (pattern, risk) in self.PATTERNS.items():
                for match in pattern.finditer(text):
                    value = match.group()
                    preview = self._mask_value(value)
                    findings.append(
                        PHIFinding(
                            phi_type=phi_type,
                            value_preview=preview,
                            location=f"pos {match.start()}-{match.end()}",
                            confidence=(
                                0.9 if risk == "high"
                                else (0.7 if risk == "medium" else 0.4)
                            ),
                            risk=risk,
                        )
                    )

            return PHIValidationReport(
                findings=findings,
                total_findings=len(findings),
                has_phi=len(findings) > 0,
                passed=len(findings) == 0,
                summary=(
                    f"Found {len(findings)} PHI finding(s)."
                    if findings
                    else "No PHI detected."
                ),
            )
        except Exception as e:
            raise PHIValidationError(f"PHI validation failed: {e}") from e

    @staticmethod
    def _mask_value(value: str) -> str:
        if len(value) <= 4:
            return "***"
        return value[0] + "*" * (len(value) - 2) + value[-1]
