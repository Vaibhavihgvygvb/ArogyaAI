import re

from app.ai.medical.engine.schemas import IntentCandidate, IntentResult

_SYMPTOM_PATTERNS = [
    r"\b(symptom|pain|ache|discomfort|fatigue|fever|cough|nausea|dizziness|headache)\b",
    r"\b(feeling|experiencing|suffering from|complaint)\b",
    r"\b(how long|when did|duration|frequency|how severe)\b",
]

_DISEASE_PATTERNS = [
    r"\b(what is|define|explain|tell me about|describe)\b",
    r"\b(condition|disease|disorder|syndrome|diagnosis)\b",
    r"\b(cancer|diabetes|hypertension|asthma|copd|arthritis)\b",
]

_MEDICATION_PATTERNS = [
    r"\b(drug|medication|medicine|prescribe|dosage|dose|pharma)\b",
    r"\b(side effect|adverse|contraindication|interaction)\b",
    r"\b(antibiotic|analgesic|antihypertensive|antidepressant|statin|metformin)\b",
    r"\b(dosage|dosing|how (much|many).*take|what.*dose)\b",
]

_PRESCRIPTION_PATTERNS = [
    r"\b(prescription|my medicine|what am I taking|why am I taking)\b",
    r"\b(prescribed|prescription refill)\b",
]

_LAB_PATTERNS = [
    r"\b(lab|test result|blood work|report|level|value)\b",
    r"\b(cbc|bmp|lft|lipid panel|thyroid panel|a1c)\b",
]

_APPOINTMENT_PATTERNS = [
    r"\b(appointment|schedule|book|reschedule|cancel)\b",
    r"\b(see doctor|consult|visit|follow up)\b",
]

_PREVENTION_PATTERNS = [
    r"\b(prevent|prevention|vaccine|screening|checkup)\b",
    r"\b(wellness|lifestyle|risk reduction|early detection)\b",
]

_EMERGENCY_PATTERNS = [
    r"\b(emergency|unconscious|not breathing|cardiac arrest)\b",
    r"\b(severe bleeding|overdose|poisoning|trauma|life threatening)\b",
]

_MENTAL_HEALTH_PATTERNS = [
    r"\b(anxiety|depression|stress|mental health|mood)\b",
    r"\b(therapy|counseling|panic|suicide|ptsd|ocd|adhd)\b",
    r"\b(anxious|depressed|suicidal|bipolar|psychotic)\b",
]

_LIFESTYLE_PATTERNS = [
    r"\b(diet|exercise|nutrition|sleep|smoking|alcohol)\b",
    r"\b(weight|fitness|physical activity|stress management)\b",
]

_NUTRITION_PATTERNS = [
    r"\b(nutrition|food|vitamin|supplement|calorie|meal)\b",
    r"\b(dietary|mineral|antioxidant|probiotic)\b",
]

_VACCINATION_PATTERNS = [
    r"\b(vaccine|vaccination|immunization|shot|booster)\b",
    r"\b(flu shot|covid vaccine|childhood vaccine)\b",
]

_FOLLOW_UP_PATTERNS = [
    r"\b(follow up|what about|and then|how about)\b",
    r"\b(also|another question|one more)\b",
]

_ADMIN_PATTERNS = [
    r"\b(bill|insurance|claim|referral|form|document)\b",
    r"\b(policy|HIPAA|privacy|medical records request)\b",
]

_INTENT_CLASSIFIERS: dict[str, list[str]] = {
    "symptom_inquiry": _SYMPTOM_PATTERNS,
    "disease_information": _DISEASE_PATTERNS,
    "medication_information": _MEDICATION_PATTERNS,
    "prescription_explanation": _PRESCRIPTION_PATTERNS,
    "lab_report_interpretation": _LAB_PATTERNS,
    "appointment_inquiry": _APPOINTMENT_PATTERNS,
    "preventive_care": _PREVENTION_PATTERNS,
    "emergency": _EMERGENCY_PATTERNS,
    "mental_health": _MENTAL_HEALTH_PATTERNS,
    "lifestyle_guidance": _LIFESTYLE_PATTERNS,
    "nutrition": _NUTRITION_PATTERNS,
    "vaccination": _VACCINATION_PATTERNS,
    "follow_up": _FOLLOW_UP_PATTERNS,
    "administrative": _ADMIN_PATTERNS,
}


class RuleBasedIntentClassifier:
    def classify(self, query: str) -> IntentResult:
        query_lower = query.lower()
        scores: dict[str, float] = {}

        for intent_name, patterns in _INTENT_CLASSIFIERS.items():
            score = 0.0
            for pattern in patterns:
                matches = re.findall(pattern, query_lower, re.IGNORECASE)
                score += len(matches) * 1.0
            if score > 0:
                scores[intent_name] = score

        if not scores:
            return IntentResult(
                primary_intent=IntentCandidate(
                    intent_type="general_inquiry",
                    confidence=0.5,
                    matched_keywords=[],
                ),
                candidates=[IntentCandidate(intent_type="general_inquiry", confidence=0.5)],
                total_candidates=1,
            )

        total_score = sum(scores.values())
        candidates = [
            IntentCandidate(
                intent_type=name,
                confidence=round(score / total_score, 4),
                matched_keywords=list(set(re.findall(r'\b\w+\b', query_lower))),
            )
            for name, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
        ]

        return IntentResult(
            primary_intent=candidates[0],
            candidates=candidates[:5],
            total_candidates=len(candidates),
        )
