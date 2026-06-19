from pydantic_settings import BaseSettings


class AssistantSettings(BaseSettings):
    ASSISTANT_ENABLED: bool = True
    ASSISTANT_MAX_MESSAGE_LENGTH: int = 10000
    ASSISTANT_MAX_HISTORY_MESSAGES: int = 50
    ASSISTANT_CONTEXT_SUMMARY_TOKENS: int = 512
    ASSISTANT_DEFAULT_TEMPERATURE: float = 0.7
    ASSISTANT_DEFAULT_MAX_TOKENS: int = 2048
    ASSISTANT_SESSION_TIMEOUT_MINUTES: int = 30
    ASSISTANT_MAX_CONVERSATIONS_PER_USER: int = 100
    ASSISTANT_ENABLE_PERSONALIZATION: bool = True
    ASSISTANT_ENABLE_CONTEXT_SUMMARIES: bool = True
    ASSISTANT_ENABLE_EMERGENCY_DETECTION: bool = True
    ASSISTANT_ENABLE_EVIDENCE_VALIDATION: bool = True
    ASSISTANT_ENABLE_SAFETY_VALIDATION: bool = True
    ASSISTANT_REQUIRE_CITATIONS: bool = True
    ASSISTANT_DEFAULT_LANGUAGE: str = "en"
    ASSISTANT_DEFAULT_AUDIENCE: str = "patient"
    ASSISTANT_DEFAULT_LITERACY_LEVEL: str = "standard"
    ASSISTANT_FALLBACK_MESSAGE: str = "I'm unable to process your request at this moment. Please try again or consult a healthcare professional."
    ASSISTANT_EMERGENCY_MESSAGE: str = "🚨 **This appears to be a medical emergency.** Please call your local emergency services immediately or go to the nearest emergency room. Do not rely on AI for emergency medical decisions."
