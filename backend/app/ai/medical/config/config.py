from pydantic_settings import BaseSettings


class MedicalSettings(BaseSettings):
    MEDICAL_ENABLED: bool = True
    MEDICAL_DEFAULT_SPECIALTY: str = "general_medicine"
    MEDICAL_SUPPORTED_SPECIALTIES: str = (
        "cardiology,neurology,oncology,pediatrics,orthopedics,dermatology,"
        "gastroenterology,pulmonology,endocrinology,psychiatry,ophthalmology,"
        "urology,nephrology,rheumatology,infectious_disease,general_medicine,"
        "emergency_medicine,anesthesiology,pathology,radiology"
    )
    MEDICAL_DEFAULT_TOP_K: int = 10
    MEDICAL_MAX_CONTEXT_TOKENS: int = 4096
    MEDICAL_MIN_CONFIDENCE_THRESHOLD: float = 0.3
    MEDICAL_REWRITE_ENABLED: bool = True
    MEDICAL_SAFETY_ENABLED: bool = True
    MEDICAL_CITATIONS_REQUIRED: bool = True
    MEDICAL_REASONING_ENABLED: bool = True
    MEDICAL_MAX_QUERY_LENGTH: int = 5000
    MEDICAL_DEFAULT_URGENCY: str = "routine"

    @property
    def specialties(self) -> list[str]:
        return [s.strip() for s in self.MEDICAL_SUPPORTED_SPECIALTIES.split(",")]

    @property
    def urgency_levels(self) -> dict[str, list[str]]:
        return {
            "critical": ["emergency", "life_threatening", "immediate"],
            "high": ["severe", "urgent", "rapid"],
            "medium": ["moderate", "concerning", "worsening"],
            "low": ["mild", "minor", "stable"],
            "routine": ["follow_up", "checkup", "general"],
        }
