import re

from app.ai.medical.exceptions.exceptions import IntentDetectionError
from app.ai.medical.interfaces.interfaces import IntentDetectorABC
from app.ai.medical.schemas.schemas import (
    IntentType,
    MedicalIntent,
    Specialty,
    UrgencyLevel,
)

_INTENT_PATTERNS: dict[IntentType, list[str]] = {
    IntentType.DIAGNOSIS: [
        r"\b(diagnos|diagnosis|identify|what (is|are|could).*(condition|disease|disorder|syndrome))\b",
        r"\b(symptoms of|signs of|indicate|suggestive of)\b",
        r"\b(differential|working diagnosis|rule out)\b",
    ],
    IntentType.TREATMENT: [
        r"\b(treat|treatment|therapy|therapeutic|manage|management)\b",
        r"\b(protocol|regimen|course of action|intervention)\b",
        r"\b(how to (treat|manage|handle|cure))\b",
    ],
    IntentType.MEDICATION: [
        r"\b(drug|medication|medicine|prescribe|dosage|dose|pharma)\b",
        r"\b(side effect|adverse|contraindication|interaction)\b",
        r"\b(antibiotic|analgesic|antihypertensive|antidepressant|statin)\b",
    ],
    IntentType.SYMPTOM_ASSESSMENT: [
        r"\b(symptom|complaint|pain|ache|discomfort|fatigue|fever)\b",
        r"\b(how (long|severe|bad)|when did|duration|frequency)\b",
        r"\b(feeling|experiencing|suffering from)\b",
    ],
    IntentType.PROCEDURE: [
        r"\b(surgery|surgical|procedure|operation|intervention)\b",
        r"\b(biopsy|endoscopy|colonoscopy|angiography|catheter)\b",
        r"\b(laparoscopy|arthroscopy|bypass|transplant|resection)\b",
    ],
    IntentType.PREVENTION: [
        r"\b(prevent|prevention|prophylaxis|vaccine|vaccination)\b",
        r"\b(screening|early detection|risk reduction|lifestyle)\b",
        r"\b(how to avoid|reduce risk|preventive|preventative)\b",
    ],
    IntentType.PROGNOSIS: [
        r"\b(prognosis|outcome|survival|recovery|life expectancy)\b",
        r"\b(prognostic|predict|expected course|long-term outlook)\b",
        r"\b(chance of|likelihood of|probability of)\b",
    ],
    IntentType.ETIOLOGY: [
        r"\b(cause|etiology|etiological|origin|pathogenesis)\b",
        r"\b(why does|what leads to|what causes|risk factor)\b",
        r"\b(trigger|precipitate|predispose|genetic|hereditary)\b",
    ],
    IntentType.EPIDEMIOLOGY: [
        r"\b(epidemiology|incidence|prevalence|mortality|morbidity)\b",
        r"\b(population|demographic|statistics|rate|ratio)\b",
        r"\b(how common|how many|frequency|occurrence)\b",
    ],
    IntentType.GENERAL_INQUIRY: [
        r"\b(what is|define|explain|describe|tell me about|overview)\b",
        r"\b(meaning|definition|information about|summary)\b",
    ],
}

_SPECIALTY_KEYWORDS: dict[Specialty, list[str]] = {
    Specialty.CARDIOLOGY: ["heart", "cardiac", "cardio", "blood pressure", "hypertension", "arrhythmia", "ecg", "echocardiogram", "angina", "infarction", "stent", "coronary", "palpitation"],
    Specialty.NEUROLOGY: ["brain", "nerve", "neurological", "stroke", "seizure", "epilepsy", "migraine", "headache", "dementia", "alzheimer", "parkinson", "neuropathy", "cerebral", "spinal"],
    Specialty.ONCOLOGY: ["cancer", "tumor", "malignancy", "oncology", "chemotherapy", "radiation", "metastasis", "carcinoma", "sarcoma", "lymphoma", "leukemia", "biopsy", "staging"],
    Specialty.PEDIATRICS: ["child", "pediatric", "infant", "newborn", "neonatal", "toddler", "adolescent", "teen", "vaccination", "growth", "development", "congenital"],
    Specialty.ORTHOPEDICS: ["bone", "joint", "fracture", "orthopedic", "spine", "arthritis", "cartilage", "ligament", "tendon", "muscle", "skeletal", "disc", "knee", "hip"],
    Specialty.DERMATOLOGY: ["skin", "rash", "dermatitis", "eczema", "psoriasis", "melanoma", "acne", "lesion", "mole", "dermatology", "fungal", "hair", "nail"],
    Specialty.GASTROENTEROLOGY: ["stomach", "intestine", "liver", "colon", "gastro", "hepatitis", "cirrhosis", "ulcer", "reflux", "gerd", "crohn", "colitis", "pancreas", "gallbladder"],
    Specialty.PULMONOLOGY: ["lung", "pulmonary", "respiratory", "breathing", "asthma", "copd", "pneumonia", "bronchitis", "emphysema", "ventilation", "oxygen", "spirometry"],
    Specialty.ENDOCRINOLOGY: ["diabetes", "thyroid", "hormone", "endocrine", "insulin", "glucose", "cortisol", "estrogen", "testosterone", "pituitary", "adrenal", "metabolic"],
    Specialty.PSYCHIATRY: ["depression", "anxiety", "psychiatric", "mental", "bipolar", "schizophrenia", "psychosis", "ptsd", "ocd", "adhd", "behavioral", "mood", "suicide"],
    Specialty.OPHTHALMOLOGY: ["eye", "vision", "retina", "cataract", "glaucoma", "ophthal", "corneal", "blindness", "visual", "optic", "lens", "intraocular"],
    Specialty.UROLOGY: ["urinary", "kidney", "bladder", "prostate", "urology", "incontinence", "uti", "nephrolithiasis", "stone", "urethra", "testicular"],
    Specialty.NEPHROLOGY: ["kidney", "renal", "nephro", "dialysis", "glomerulo", "creatinine", "bun", "nephrotic", "nephritic", "electrolyte"],
    Specialty.RHEUMATOLOGY: ["rheumatoid", "arthritis", "autoimmune", "lupus", "gout", "rheumatic", "vasculitis", "scleroderma", "sjogren", "inflammatory", "joint pain"],
    Specialty.INFECTIOUS_DISEASE: ["infection", "infectious", "fever", "virus", "bacterial", "fungal", "sepsis", "hiv", "tuberculosis", "covid", "antibiotic", "contagious"],
    Specialty.GENERAL_MEDICINE: ["general", "primary", "checkup", "physical", "wellness", "preventive", "screening", "routine", "comprehensive"],
    Specialty.EMERGENCY_MEDICINE: ["emergency", "critical", "trauma", "resuscitation", "acute", "life threatening", "urgent", "overdose", "poisoning", "shock"],
    Specialty.ANESTHESIOLOGY: ["anesthesia", "anesthetic", "sedation", "pain management", "intubation", "airway", "perioperative", "block"],
    Specialty.PATHOLOGY: ["pathology", "biopsy", "histology", "cytology", "lab results", "specimen", "microscopy", "staining"],
    Specialty.RADIOLOGY: ["radiology", "xray", "x-ray", "mri", "ct scan", "ultrasound", "imaging", "radiograph", "contrast", "fluoroscopy"],
}

_URGENCY_KEYWORDS: dict[UrgencyLevel, list[str]] = {
    UrgencyLevel.CRITICAL: ["emergency", "life threatening", "immediate", "cardiac arrest", "sepsis", "stroke", "anaphylaxis", "unconscious", "not breathing", "severe bleeding"],
    UrgencyLevel.HIGH: ["severe", "urgent", "rapid", "worsening", "acute", "intense", "debilitating", "excruciating", "hospitalize", "er"],
    UrgencyLevel.MEDIUM: ["moderate", "concerning", "worsening", "persistent", "chronic", "recurring", "seek care", "appointment"],
    UrgencyLevel.LOW: ["mild", "minor", "stable", "manageable", "slight", "occasional", "temporary"],
    UrgencyLevel.ROUTINE: ["follow up", "checkup", "routine", "screening", "general", "annual", "regular", "refill"],
}

_ABBREVIATIONS: dict[str, str] = {
    "sob": "shortness of breath",
    "cva": "cerebrovascular accident",
    "mi": "myocardial infarction",
    "htn": "hypertension",
    "dm": "diabetes mellitus",
    "copd": "chronic obstructive pulmonary disease",
    "uti": "urinary tract infection",
    "gi": "gastrointestinal",
    "gu": "genitourinary",
    "cxr": "chest x-ray",
    "ekg": "electrocardiogram",
    "lft": "liver function test",
    "bmp": "basic metabolic panel",
    "cbc": "complete blood count",
    "bp": "blood pressure",
    "hr": "heart rate",
    "rr": "respiratory rate",
    "temp": "temperature",
    "oed": "occupational exposure dose",
    "tbi": "traumatic brain injury",
    "cabg": "coronary artery bypass graft",
    "pvd": "peripheral vascular disease",
    "dvt": "deep vein thrombosis",
    "pe": "pulmonary embolism",
    "tia": "transient ischemic attack",
    "sbo": "small bowel obstruction",
    "aro": "acute renal obstruction",
}


class IntentDetector(IntentDetectorABC):
    async def detect(self, query: str, specialty_hint: str | None = None) -> MedicalIntent:
        query_lower = query.lower()
        intent_type = self._detect_intent(query_lower)
        specialty = self._detect_specialty(query_lower, specialty_hint)
        urgency = self._detect_urgency(query_lower)
        keywords = self._extract_keywords(query_lower, specialty)

        return MedicalIntent(
            intent_type=intent_type,
            specialty=specialty,
            urgency=urgency,
            confidence=0.8,
            keywords=keywords,
        )

    def _detect_intent(self, query: str) -> IntentType:
        scores: dict[IntentType, int] = {}
        for intent_type, patterns in _INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                score += len(matches)
            if score > 0:
                scores[intent_type] = score
        if not scores:
            return IntentType.GENERAL_INQUIRY
        return max(scores, key=scores.get)

    def _detect_specialty(self, query: str, hint: str | None = None) -> Specialty:
        if hint:
            for sp in Specialty:
                if sp.value == hint.lower().replace(" ", "_"):
                    return sp

        scores: dict[Specialty, int] = {}
        for specialty, keywords in _SPECIALTY_KEYWORDS.items():
            score = 0
            for kw in keywords:
                if kw in query:
                    score += 1
            if score > 0:
                scores[specialty] = score
        if not scores:
            return Specialty.GENERAL_MEDICINE
        return max(scores, key=scores.get)

    def _detect_urgency(self, query: str) -> UrgencyLevel:
        for level in [UrgencyLevel.CRITICAL, UrgencyLevel.HIGH, UrgencyLevel.MEDIUM, UrgencyLevel.LOW]:
            for kw in _URGENCY_KEYWORDS[level]:
                if kw in query:
                    return level
        return UrgencyLevel.ROUTINE

    def _extract_keywords(self, query: str, specialty: Specialty) -> list[str]:
        words = set()
        for kw in _SPECIALTY_KEYWORDS.get(specialty, []):
            if kw in query:
                words.add(kw)
        for intent_patterns in _INTENT_PATTERNS.values():
            for pattern in intent_patterns:
                matches = re.findall(pattern, query, re.IGNORECASE)
                for m in matches:
                    if isinstance(m, tuple):
                        for g in m:
                            if g:
                                words.add(g.strip().lower())
                    elif isinstance(m, str):
                        words.add(m.strip().lower())
        medical_terms = [
            "acute", "chronic", "severe", "mild", "moderate", "pain", "fever",
            "infection", "inflammation", "swelling", "nausea", "vomiting",
            "fatigue", "weight loss", "dizziness", "shortness of breath",
        ]
        for term in medical_terms:
            if term in query:
                words.add(term)
        return sorted(words)
