from pydantic_settings import BaseSettings


class ResponseSettings(BaseSettings):
    RESPONSE_ENABLED: bool = True
    RESPONSE_DEFAULT_TEMPERATURE: float = 0.7
    RESPONSE_DEFAULT_MAX_TOKENS: int = 2048
    RESPONSE_MAX_TOKENS: int = 16384
    RESPONSE_STREAMING_ENABLED: bool = True
    RESPONSE_STREAMING_CHUNK_SIZE: int = 50
    RESPONSE_STRUCTURED_OUTPUT_ENABLED: bool = True
    RESPONSE_CITATIONS_INLINE: bool = True
    RESPONSE_DISCLAIMER_ENABLED: bool = True
    RESPONSE_DISCLAIMER_TEXT: str = (
        "This information is for educational purposes only and does not "
        "constitute medical advice. Always consult a qualified healthcare "
        "professional for medical decisions."
    )
    RESPONSE_EMERGENCY_DISCLAIMER: str = (
        "THIS IS AN EMERGENCY — If you are experiencing a medical emergency, "
        "call your local emergency services immediately. Do not wait for an "
        "online response."
    )
    RESPONSE_INCLUDE_METADATA: bool = True
    RESPONSE_SECTION_FORMATTING: bool = True
    RESPONSE_MAX_SECTIONS: int = 10
    RESPONSE_DEFAULT_MODEL: str = ""
    RESPONSE_DEFAULT_PROVIDER: str = ""
    RESPONSE_FALLBACK_ON_ERROR: bool = True
    RESPONSE_FALLBACK_MESSAGE: str = (
        "I'm unable to generate a complete response at this time. "
        "Please try rephrasing your question or consult a healthcare professional."
    )
