import re

from app.ai.clinical_safety.exceptions import EmergencyDetectionError
from app.ai.clinical_safety.interfaces.emergency import EmergencyDetector
from app.ai.clinical_safety.schemas import (
    EmergencyReport,
    EmergencyResult,
    EmergencyType,
)


class DefaultEmergencyDetector(EmergencyDetector):

    RECOMMENDED_ACTION = (
        "Seek immediate emergency medical attention. Call emergency services."
    )

    SEVERITY_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}

    PATTERNS: dict[EmergencyType, list[tuple[re.Pattern, float, str]]] = {
        EmergencyType.CHEST_PAIN: [
            (
                re.compile(
                    r'\bchest\s*(?:pain|tightness|pressure|discomfort)\b',
                    re.IGNORECASE,
                ),
                0.95,
                "high",
            ),
            (
                re.compile(
                    r'\b(?:pressure|tightness)\s+in\s+(?:the\s+)?chest\b',
                    re.IGNORECASE,
                ),
                0.90,
                "high",
            ),
        ],
        EmergencyType.STROKE_SYMPTOMS: [
            (
                re.compile(r'\bsudden\s+numbness\b', re.IGNORECASE),
                0.85,
                "high",
            ),
            (
                re.compile(r'\bweakness\s+on\s+one\s+side\b', re.IGNORECASE),
                0.85,
                "high",
            ),
            (
                re.compile(r'\bslurred\s+speech\b', re.IGNORECASE),
                0.85,
                "high",
            ),
            (
                re.compile(r'\bface\s+drooping\b', re.IGNORECASE),
                0.85,
                "high",
            ),
            (
                re.compile(r'\bfacial\s+droop\b', re.IGNORECASE),
                0.85,
                "high",
            ),
            (
                re.compile(r'\bstroke\s*symptoms?\b', re.IGNORECASE),
                0.70,
                "medium",
            ),
        ],
        EmergencyType.SEVERE_BLEEDING: [
            (
                re.compile(r'\bsevere\s+bleeding\b', re.IGNORECASE),
                0.95,
                "high",
            ),
            (
                re.compile(r'\buncontrolled\s+bleeding\b', re.IGNORECASE),
                0.95,
                "high",
            ),
            (
                re.compile(r'\bhemorrhage\b', re.IGNORECASE),
                0.90,
                "high",
            ),
        ],
        EmergencyType.SUICIDAL_IDEATION: [
            (
                re.compile(r'\bsuicide\b', re.IGNORECASE),
                0.95,
                "critical",
            ),
            (
                re.compile(r'\bkill\s+myself\b', re.IGNORECASE),
                0.98,
                "critical",
            ),
            (
                re.compile(r'\bwant\s+to\s+die\b', re.IGNORECASE),
                0.90,
                "critical",
            ),
            (
                re.compile(r'\bself[\s-]?harm\b', re.IGNORECASE),
                0.85,
                "high",
            ),
            (
                re.compile(r'\bsuicidal\b', re.IGNORECASE),
                0.95,
                "critical",
            ),
        ],
        EmergencyType.ANAPHYLAXIS: [
            (
                re.compile(r'\banaphylaxis\b', re.IGNORECASE),
                0.95,
                "high",
            ),
            (
                re.compile(r'\bsevere\s+allergic\s+reaction\b', re.IGNORECASE),
                0.90,
                "high",
            ),
            (
                re.compile(
                    r'\btrouble\s+breathing\s+after\s+medication\b',
                    re.IGNORECASE,
                ),
                0.85,
                "high",
            ),
        ],
        EmergencyType.RESPIRATORY_DISTRESS: [
            (
                re.compile(r'\bdifficulty\s+breathing\b', re.IGNORECASE),
                0.90,
                "high",
            ),
            (
                re.compile(r'\bshortness\s+of\s+breath\b', re.IGNORECASE),
                0.85,
                "high",
            ),
            (
                re.compile(r'\bcan\'\s*t\s+breathe\b', re.IGNORECASE),
                0.95,
                "critical",
            ),
            (
                re.compile(r'\bcannot\s+breathe\b', re.IGNORECASE),
                0.90,
                "high",
            ),
        ],
        EmergencyType.LOSS_OF_CONSCIOUSNESS: [
            (
                re.compile(r'\bpassed\s+out\b', re.IGNORECASE),
                0.85,
                "high",
            ),
            (
                re.compile(r'\bunconscious\b', re.IGNORECASE),
                0.95,
                "critical",
            ),
            (
                re.compile(r'\bfainted\b', re.IGNORECASE),
                0.80,
                "medium",
            ),
            (
                re.compile(
                    r'\bloss\s+of\s+consciousness\b', re.IGNORECASE
                ),
                0.95,
                "high",
            ),
        ],
    }

    def __init__(self, config=None):
        self.config = config

    async def detect(
        self,
        text: str,
        claims: list[str],
    ) -> EmergencyReport:
        try:
            combined = text
            if claims:
                combined = text + " " + " ".join(claims)

            results: list[EmergencyResult] = []

            for emergency_type, pattern_list in self.PATTERNS.items():
                for pattern, confidence, severity in pattern_list:
                    matches = pattern.findall(combined)
                    if matches:
                        results.append(
                            EmergencyResult(
                                is_emergency=True,
                                emergency_type=emergency_type,
                                confidence=confidence,
                                indicators=list(set(matches))[:5],
                                severity=severity,
                                recommended_action=self.RECOMMENDED_ACTION,
                                disclaimer_required=True,
                                details=(
                                    f"Detected {emergency_type.value}: "
                                    f"{len(matches)} match(es)."
                                ),
                            )
                        )
                        break

            has_emergency = len(results) > 0
            max_severity = "none"
            if results:
                max_severity = max(
                    (r.severity for r in results),
                    key=lambda s: self.SEVERITY_ORDER.get(s, 0),
                )

            requires_override = any(
                r.severity in ("high", "critical") for r in results
            )

            return EmergencyReport(
                results=results,
                has_emergency=has_emergency,
                max_severity=max_severity,
                requires_override=requires_override,
                summary=(
                    f"Detected {len(results)} emergency type(s). "
                    f"Max severity: {max_severity}."
                ),
            )
        except Exception as e:
            raise EmergencyDetectionError(
                f"Emergency detection failed: {e}"
            ) from e
