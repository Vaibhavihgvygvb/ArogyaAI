from app.ai.medical.engine.schemas import MedicalEntity, EntityResult, EntityType
import re


_SYMPTOM_PATTERNS = [
    (r"\b(headache|migraine|dizziness|vertigo|fever|cough|cold|flu)\b", "symptom"),
    (r"\b(pain|ache|sore|tender|swelling|inflammation|nausea|vomiting)\b", "symptom"),
    (r"\b(fatigue|weakness|numbness|tingling|blurred vision|chest pain)\b", "symptom"),
    (r"\b(shortness of breath|sob|palpitation|seizure|convulsion)\b", "symptom"),
]

_DISEASE_PATTERNS = [
    (r"\b(diabetes|hypertension|asthma|copd|arthritis|cancer)\b", "disease"),
    (r"\b(pneumonia|tuberculosis|malaria|dengue|typhoid|hepatitis)\b", "disease"),
    (r"\b(covid|stroke|heart disease|kidney disease|liver disease)\b", "disease"),
    (r"\b(anemia|thyroid|depression|anxiety|migraine|epilepsy)\b", "disease"),
]

_MEDICATION_PATTERNS = [
    (r"\b(paracetamol|ibuprofen|aspirin|metformin|insulin|amlodipine)\b", "medication"),
    (r"\b(atorvastatin|lisinopril|omeprazole|prednisone|levothyroxine)\b", "medication"),
    (r"\b(antibiotic|antidepressant|antihypertensive|statin|analgesic)\b", "medication"),
]

_PROCEDURE_PATTERNS = [
    (r"\b(surgery|biopsy|endoscopy|colonoscopy|angiography)\b", "procedure"),
    (r"\b(mri|ct scan|xray|ultrasound|echocardiogram|ekg)\b", "procedure"),
    (r"\b(dialysis|ventilation|intubation|catheter|transplant)\b", "procedure"),
]

_LAB_PATTERNS = [
    (r"\b(cbc|bmp|lft|lipid panel|a1c|thyroid panel)\b", "lab_test"),
    (r"\b(blood test|urine test|stool test|biopsy result|pathology)\b", "lab_test"),
]

_VITAL_PATTERNS = [
    (r"\b(blood pressure|bp|heart rate|pulse|temperature|oxygen)\b", "vital_sign"),
    (r"\b(weight|height|bmi|respiratory rate|rr|spo2)\b", "vital_sign"),
]

_ANATOMY_PATTERNS = [
    (r"\b(heart|liver|kidney|lung|brain|stomach|intestine|colon)\b", "anatomy"),
    (r"\b(spine|bone|joint|muscle|nerve|artery|vein|skin)\b", "anatomy"),
]

_ALLERGY_PATTERNS = [
    (r"\b(allergy|allergic|anaphylaxis|hives|rash)\b", "allergy"),
    (r"\b(peanut|lactose|gluten|pollen|dust|penicillin)\b", "allergy"),
]

_DOSAGE_PATTERNS = [
    (r"\b(\d+\s*mg|\d+\s*ml|\d+\s*mcg|\d+\s*g|\d+\s*tablet)\b", "dosage"),
    (r"\b(twice daily|once daily|three times|every \d+ hours|as needed)\b", "dosage"),
]

_TIME_PATTERNS = [
    (r"\b(\d+\s*(day|week|month|year|hour|minute)s?\s+(ago|for|now))\b", "time_expression"),
    (r"\b(yesterday|today|last week|last month|morning|evening|night)\b", "time_expression"),
]

_AGE_PATTERNS = [
    (r"\b(\d+\s*(year|month|week|day)\s*old)\b", "age_reference"),
    (r"\b(newborn|infant|toddler|child|adult|elderly|geriatric)\b", "age_reference"),
]

_CHRONIC_PATTERNS = [
    (r"\b(chronic|long term|ongoing|persistent|recurring)\b", "chronic_condition"),
    (r"\b(managed|history of|diagnosed with|suffers from)\b", "chronic_condition"),
]

_ALL_PATTERNS = (
    _SYMPTOM_PATTERNS + _DISEASE_PATTERNS + _MEDICATION_PATTERNS +
    _PROCEDURE_PATTERNS + _LAB_PATTERNS + _VITAL_PATTERNS +
    _ANATOMY_PATTERNS + _ALLERGY_PATTERNS + _DOSAGE_PATTERNS +
    _TIME_PATTERNS + _AGE_PATTERNS + _CHRONIC_PATTERNS
)


class RuleBasedEntityExtractor:
    def extract(self, query: str) -> EntityResult:
        query_lower = query.lower()
        entities: list[MedicalEntity] = []
        seen: set[str] = set()

        for pattern, entity_type_str in _ALL_PATTERNS:
            for match in re.finditer(pattern, query_lower, re.IGNORECASE):
                text = match.group(0)
                if text.lower() not in seen:
                    seen.add(text.lower())
                    try:
                        et = EntityType(entity_type_str)
                    except ValueError:
                        continue
                    entities.append(MedicalEntity(
                        entity_type=et,
                        text=match.group(0),
                        normalized_text=text.lower(),
                        confidence=0.8,
                        start_pos=match.start(),
                        end_pos=match.end(),
                    ))

        entities.sort(key=lambda e: e.start_pos)
        return EntityResult(entities=entities, total=len(entities))
