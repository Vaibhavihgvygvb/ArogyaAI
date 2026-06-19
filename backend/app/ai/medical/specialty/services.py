from app.ai.medical.engine.schemas import SpecialtyCandidate, SpecialtyResult
import re


_SPECIALTY_KEYWORDS: dict[str, list[str]] = {
    "cardiology": ["heart", "cardiac", "cardio", "blood pressure", "hypertension", "arrhythmia", "ecg", "angina", "infarction", "stent", "coronary", "palpitation"],
    "neurology": ["brain", "nerve", "neurological", "stroke", "seizure", "epilepsy", "migraine", "headache", "dementia", "alzheimer", "parkinson", "neuropathy", "cerebral", "spinal"],
    "endocrinology": ["diabetes", "thyroid", "hormone", "endocrine", "insulin", "glucose", "cortisol", "estrogen", "testosterone", "pituitary", "adrenal", "metabolic"],
    "oncology": ["cancer", "tumor", "malignancy", "oncology", "chemotherapy", "radiation", "metastasis", "carcinoma", "sarcoma", "lymphoma", "leukemia", "biopsy", "staging"],
    "psychiatry": ["depression", "anxiety", "psychiatric", "mental", "bipolar", "schizophrenia", "psychosis", "ptsd", "ocd", "adhd", "behavioral", "mood", "suicide"],
    "dermatology": ["skin", "rash", "dermatitis", "eczema", "psoriasis", "melanoma", "acne", "lesion", "mole", "dermatology", "fungal", "hair", "nail"],
    "pediatrics": ["child", "pediatric", "infant", "newborn", "neonatal", "toddler", "adolescent", "teen", "vaccination", "growth", "development", "congenital"],
    "orthopedics": ["bone", "joint", "fracture", "orthopedic", "spine", "arthritis", "cartilage", "ligament", "tendon", "muscle", "skeletal", "disc", "knee", "hip"],
    "pulmonology": ["lung", "pulmonary", "respiratory", "breathing", "asthma", "copd", "pneumonia", "bronchitis", "emphysema", "ventilation", "oxygen", "spirometry"],
    "gastroenterology": ["stomach", "intestine", "liver", "colon", "gastro", "hepatitis", "cirrhosis", "ulcer", "reflux", "gerd", "crohn", "colitis", "pancreas", "gallbladder"],
    "emergency_medicine": ["emergency", "critical", "trauma", "resuscitation", "acute", "life threatening", "urgent", "overdose", "poisoning", "shock"],
    "general_medicine": ["general", "primary", "checkup", "physical", "wellness", "preventive", "screening", "routine", "comprehensive"],
}


class SpecialtyClassifier:
    def __init__(self):
        self._specialties = _SPECIALTY_KEYWORDS

    def classify(self, query: str) -> SpecialtyResult:
        query_lower = query.lower()
        scores: dict[str, float] = {}

        for specialty, keywords in self._specialties.items():
            score = 0.0
            matched = []
            for kw in keywords:
                if kw in query_lower:
                    score += 1.0
                    matched.append(kw)
            if score > 0:
                scores[specialty] = score

        if not scores:
            return SpecialtyResult(
                primary_specialty=SpecialtyCandidate(
                    specialty="general_medicine",
                    confidence=0.5,
                ),
                candidates=[SpecialtyCandidate(specialty="general_medicine", confidence=0.5)],
                total_candidates=1,
            )

        total = sum(scores.values())
        candidates = [
            SpecialtyCandidate(
                specialty=name,
                confidence=round(score / total, 4),
                matched_terms=[],
            )
            for name, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)
        ]

        return SpecialtyResult(
            primary_specialty=candidates[0],
            candidates=candidates[:5],
            total_candidates=len(candidates),
        )
