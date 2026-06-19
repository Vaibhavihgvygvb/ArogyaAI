import re
from app.ai.medical.engine.schemas import AudienceResult, AudienceType


_AUDIENCE_PATTERNS: dict[AudienceType, list[str]] = {
    AudienceType.PATIENT: [
        r"\b(i feel|my (pain|symptom|medication|condition|treatment|health|body))\b",
        r"\b(should I|can I|am I|do I need)\b",
        r"\b(what should I do|how do I|when should I)\b",
        r"\b(i have been|i am|i was|i went)\b",
    ],
    AudienceType.DOCTOR: [
        r"\b(the patient|this patient|my patient)\b",
        r"\b(diagnosis|differential|management plan|treatment plan)\b",
        r"\b(prescribe|dosage|regimen|clinical trial)\b",
        r"\b(referral|consult|specialist)\b",
        r"\b(lab results|imaging|pathology report|vital signs)\b",
    ],
    AudienceType.NURSE: [
        r"\b(vital signs|medication administration|wound care)\b",
        r"\b(monitor|assessment|observation|nursing)\b",
    ],
    AudienceType.CAREGIVER: [
        r"\b(my (mother|father|parent|child|spouse|husband|wife|sister|brother|son|daughter))\b",
        r"\b(care for|look after|help them|they need)\b",
    ],
    AudienceType.ADMINISTRATOR: [
        r"\b(bill|insurance|claim|policy|compliance|regulation)\b",
        r"\b(audit|report|documentation|record keeping)\b",
    ],
}


class AudienceClassifier:
    def classify(self, query: str) -> AudienceResult:
        query_lower = query.lower()
        scores: dict[AudienceType, float] = {}

        for audience_type, patterns in _AUDIENCE_PATTERNS.items():
            score = 0.0
            for pattern in patterns:
                matches = re.findall(pattern, query_lower, re.IGNORECASE)
                score += len(matches)
            if score > 0:
                scores[audience_type] = score

        if not scores:
            return AudienceResult(
                audience=AudienceType.UNKNOWN,
                confidence=0.5,
                indicators=["No audience indicators detected"],
            )

        best = max(scores, key=scores.get)
        return AudienceResult(
            audience=best,
            confidence=round(min(scores[best] / 5.0, 0.95), 4),
            indicators=[pattern for audience_type, pattern_list in _AUDIENCE_PATTERNS.items() for indicator in re.findall(pattern_list[0] if pattern_list else "", query_lower)],
        )
