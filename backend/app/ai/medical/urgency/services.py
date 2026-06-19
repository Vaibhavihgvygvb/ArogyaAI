import re
from app.ai.medical.engine.schemas import UrgencyResult


_URGENCY_PATTERNS: dict[str, list[str]] = {
    "emergency": ["emergency", "life threatening", "immediate", "cardiac arrest", "sepsis", "stroke",
                  "anaphylaxis", "unconscious", "not breathing", "severe bleeding", "overdose",
                  "poisoning", "trauma", "shock", "respiratory failure", "code blue"],
    "urgent": ["severe", "urgent", "rapid", "worsening", "acute", "intense", "debilitating",
               "excruciating", "hospitalize", "er", "can't breathe", "chest pain",
               "seizure", "paralysis", "vision loss"],
    "routine": ["mild", "minor", "stable", "manageable", "slight", "occasional", "temporary",
                "follow up", "checkup", "routine", "screening", "general", "annual", "regular"],
    "informational": ["what is", "define", "explain", "tell me about", "describe", "overview",
                      "meaning", "information", "education", "learn about"],
}


class UrgencyClassifier:
    def __init__(self):
        self._patterns = _URGENCY_PATTERNS

    def classify(self, query: str) -> UrgencyResult:
        query_lower = query.lower()

        for pattern in self._patterns["emergency"]:
            if pattern in query_lower:
                return UrgencyResult(
                    level="emergency",
                    confidence=0.9,
                    indicators=["emergency: " + pattern],
                    is_emergency=True,
                )

        for pattern in self._patterns["urgent"]:
            if pattern in query_lower:
                return UrgencyResult(
                    level="urgent",
                    confidence=0.7,
                    indicators=["urgent: " + pattern],
                    is_emergency=False,
                )

        for pattern in self._patterns["informational"]:
            if pattern in query_lower:
                return UrgencyResult(
                    level="informational",
                    confidence=0.7,
                    indicators=["informational: " + pattern],
                    is_emergency=False,
                )

        return UrgencyResult(
            level="routine",
            confidence=0.5,
            indicators=[],
            is_emergency=False,
        )
