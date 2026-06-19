import time
from typing import Any


def timing_ms(start: float) -> float:
    return round((time.time() - start) * 1000, 2)


def extract_topics(text: str) -> list[str]:
    topic_keywords = {
        "symptom": ["symptom", "pain", "ache", "hurt", "fever", "cough", "fatigue", "nausea", "dizziness"],
        "medication": ["medication", "medicine", "drug", "pill", "dose", "dosage", "prescription", "tablet"],
        "disease": ["disease", "condition", "disorder", "syndrome", "infection", "illness"],
        "treatment": ["treatment", "therapy", "procedure", "surgery", "operation", "remedy"],
        "diagnosis": ["diagnosis", "test", "lab", "scan", "xray", "mri", "blood", "result"],
        "prevention": ["prevent", "vaccine", "vaccination", "immunization", "screening"],
        "lifestyle": ["diet", "exercise", "nutrition", "sleep", "stress", "weight", "smoking", "alcohol"],
        "mental_health": ["anxiety", "depression", "stress", "mental", "therapy", "counseling", "psychiatrist"],
        "appointment": ["appointment", "doctor", "clinic", "hospital", "visit", "checkup", "follow"],
        "emergency": ["emergency", "urgent", "severe", "critical", "immediate", "ambulance", "er"],
    }
    text_lower = text.lower()
    topics = []
    for topic, keywords in topic_keywords.items():
        for kw in keywords:
            if kw in text_lower:
                topics.append(topic)
                break
    return topics
