from pydantic import BaseModel, Field


class IntentCategory(BaseModel):
    name: str
    display_name: str
    description: str
    patterns: list[str] = Field(default_factory=list)
    priority: int = 0


INTENT_CATEGORIES: list[IntentCategory] = [
    IntentCategory(name="symptom_inquiry", display_name="Symptom Inquiry", description="User is describing or asking about symptoms", patterns=["symptom", "pain", "ache", "discomfort", "fatigue", "fever", "feeling", "experiencing", "suffering from"], priority=10),
    IntentCategory(name="disease_information", display_name="Disease Information", description="User wants information about a specific disease", patterns=["what is", "define", "tell me about", "explain", "condition", "disease", "disorder", "syndrome", "diagnosis"], priority=9),
    IntentCategory(name="medication_information", display_name="Medication Information", description="User wants information about medications", patterns=["medication", "medicine", "drug", "dosage", "dose", "prescribe", "side effect", "contraindication", "interaction"], priority=9),
    IntentCategory(name="prescription_explanation", display_name="Prescription Explanation", description="User wants their prescription explained", patterns=["prescription", "my medicine", "what am I taking", "why am I taking", "prescribed"], priority=8),
    IntentCategory(name="lab_report_interpretation", display_name="Lab Report Interpretation", description="User wants lab results interpreted", patterns=["lab", "test result", "blood work", "report", "level", "value", "result"], priority=8),
    IntentCategory(name="medical_record_explanation", display_name="Medical Record Explanation", description="User wants medical records explained", patterns=["record", "history", "chart", "file", "documentation"], priority=7),
    IntentCategory(name="appointment_inquiry", display_name="Appointment Inquiry", description="User is asking about appointments", patterns=["appointment", "schedule", "book", "visit", "see doctor", "consult"], priority=7),
    IntentCategory(name="preventive_care", display_name="Preventive Care", description="User wants preventive care information", patterns=["prevent", "prevention", "screening", "vaccine", "checkup", "routine", "wellness", "lifestyle"], priority=6),
    IntentCategory(name="emergency", display_name="Emergency", description="User is describing an emergency", patterns=["emergency", "unconscious", "not breathing", "severe bleeding", "cardiac arrest", "overdose", "poisoning", "trauma", "life threatening"], priority=10),
    IntentCategory(name="mental_health", display_name="Mental Health", description="User is asking about mental health", patterns=["anxiety", "depression", "stress", "mental", "mood", "therapy", "counseling", "suicide", "panic"], priority=8),
    IntentCategory(name="lifestyle_guidance", display_name="Lifestyle Guidance", description="User wants lifestyle advice", patterns=["diet", "exercise", "nutrition", "sleep", "smoking", "alcohol", "weight", "fitness"], priority=5),
    IntentCategory(name="nutrition", display_name="Nutrition", description="User wants nutrition information", patterns=["nutrition", "diet", "food", "vitamin", "supplement", "calorie", "meal", "eating"], priority=5),
    IntentCategory(name="vaccination", display_name="Vaccination", description="User wants vaccination information", patterns=["vaccine", "vaccination", "immunization", "shot", "booster", "covid vaccine", "flu shot"], priority=6),
    IntentCategory(name="follow_up", display_name="Follow-up Question", description="User is following up on a previous question", patterns=["follow up", "what about", "and then", "how about", "also", "another question"], priority=4),
    IntentCategory(name="administrative", display_name="Administrative", description="User has an administrative request", patterns=["bill", "insurance", "claim", "referral", "form", "document", "policy", "HIPAA", "privacy"], priority=4),
]
