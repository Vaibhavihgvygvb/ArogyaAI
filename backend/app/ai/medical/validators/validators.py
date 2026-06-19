import re

from app.ai.medical.interfaces.interfaces import SafetyValidatorABC
from app.ai.medical.schemas.schemas import CitationEntry, IntentType, MedicalIntent, SafetyCheckResult

_UNSAFE_ADVICE_PATTERNS: list[str] = [
    r"\b(discontinue|stop taking)\s+(your\s+)?(medication|prescription|treatment)\s+(without|without consulting|abruptly)\b",
    r"\b(take\s+(more|extra|double)\s+(dose|medication|pill))\b",
    r"\b(self-diagnos|self-treat|self-medicate)\b",
    r"\b(ignore|disregard)\s+(symptom|warning|sign|medical advice)\b",
    r"\b(avoid|skip|refuse)\s+(treatment|therapy|medication|vaccination)\b",
    r"\b(use|take|administer)\s+(expired|unprescribed|someone else'?s)\s+(medication|drug|medicine)\b",
]

_CONTRADICTION_PATTERNS: list[str] = [
    r"\b(however|but|although|nevertheless|on the other hand)\s+",
    r"\b(contrary to|in contrast|contradict|inconsistent with)\b",
    r"\b(studies show|research indicates|evidence suggests)\s+(both|neither|either)\b",
]

_HALLUCINATION_INDICATORS: list[str] = [
    r"\bI am not sure\b",
    r"\bI don'?t have (enough|sufficient|specific) (information|data|knowledge)\b",
    r"\bbased on (limited|insufficient) (evidence|data|information)\b",
    r"\bno (studies|research|evidence)\s+(show|indicate|suggest|support)\b",
    r"\bthere is (no|little|insufficient)\s+(evidence|data|research)\b",
]


_CONTRAINDICATED_SPECIALTIES: dict[str, list[str]] = {
    "cardiology": ["cardiac", "heart", "cardiovascular"],
    "oncology": ["cancer", "tumor", "malignancy", "chemotherapy"],
    "psychiatry": ["suicide", "self-harm", "depression", "psychiatric"],
    "emergency_medicine": ["emergency", "trauma", "acute", "life-threatening"],
}

_KEY_PHRASES = [
    "seek immediate medical attention", "consult your doctor", "emergency department",
    "call emergency services", "this is not medical advice", "for informational purposes only",
]


class SafetyValidator(SafetyValidatorABC):
    async def validate(
        self,
        query: str,
        response: str,
        citations: list[CitationEntry],
        intent: MedicalIntent,
    ) -> SafetyCheckResult:
        warnings: list[str] = []
        response_lower = response.lower()

        hallucination_risk = self._check_hallucination_risk(response_lower, citations)
        if hallucination_risk > 0.5:
            warnings.append(f"Response has {hallucination_risk:.0%} hallucination risk — limited evidence support")

        unsafe_advice_risk = self._check_unsafe_advice(response_lower)
        if unsafe_advice_risk > 0.3:
            warnings.append(f"Response contains potentially unsafe medical advice ({unsafe_advice_risk:.0%} risk)")

        contradiction_risk = self._check_contradictions(response)
        if contradiction_risk > 0.3:
            warnings.append(f"Response contains contradictory statements ({contradiction_risk:.0%} risk)")

        specialty_contraindicated = self._check_specialty_contraindication(
            response_lower, intent.specialty.value
        )
        if specialty_contraindicated:
            warnings.append(
                f"Response discusses {intent.specialty.value.replace('_', ' ')}-contraindicated topics — "
                f"consider referral"
            )

        missing_disclaimer = True
        for phrase in _KEY_PHRASES:
            if phrase in response_lower:
                missing_disclaimer = False
                break
        if missing_disclaimer:
            warnings.append(
                "Response lacks standard medical disclaimer — add disclaimer"
            )

        passed = hallucination_risk < 0.7 and unsafe_advice_risk < 0.6 and contradiction_risk < 0.5

        reason = None
        if not passed:
            reason = f"Safety check failed: hallucination={hallucination_risk:.2f}, unsafe_advice={unsafe_advice_risk:.2f}, contradiction={contradiction_risk:.2f}"
        elif warnings:
            reason = "Safety check passed with warnings"

        return SafetyCheckResult(
            passed=passed,
            hallucination_risk=round(hallucination_risk, 4),
            unsafe_advice_risk=round(unsafe_advice_risk, 4),
            contradiction_risk=round(contradiction_risk, 4),
            warnings=warnings,
            reason=reason,
        )

    def _check_hallucination_risk(self, response: str, citations: list[CitationEntry]) -> float:
        risk = 0.0
        for pattern in _HALLUCINATION_INDICATORS:
            if re.search(pattern, response, re.IGNORECASE):
                risk += 0.15

        citation_support = sum(1 for c in citations if c.evidence_text and len(c.evidence_text.strip()) > 50)
        if citation_support == 0 and len(response.split()) > 50:
            risk += 0.3
        elif citation_support >= 3:
            risk -= 0.2

        return max(0.0, min(risk, 1.0))

    def _check_unsafe_advice(self, response: str) -> float:
        risk = 0.0
        for pattern in _UNSAFE_ADVICE_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                risk += 0.25
        return max(0.0, min(risk, 1.0))

    def _check_contradictions(self, response: str) -> float:
        matches = 0
        for pattern in _CONTRADICTION_PATTERNS:
            if re.search(pattern, response, re.IGNORECASE):
                matches += 1
        return min(matches * 0.15, 1.0)

    def _check_specialty_contraindication(self, response: str, specialty: str) -> bool:
        if specialty in _CONTRAINDICATED_SPECIALTIES:
            for term in _CONTRAINDICATED_SPECIALTIES[specialty]:
                if re.search(r'\b' + re.escape(term) + r'\b', response, re.IGNORECASE):
                    continue
            return False
        return False
