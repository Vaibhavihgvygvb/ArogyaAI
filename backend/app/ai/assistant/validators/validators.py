from app.ai.assistant.config.config import AssistantSettings
from app.ai.assistant.exceptions.exceptions import ValidationError
from app.ai.assistant.schemas.schemas import ChatRequest, ContinueRequest, ExplainRequest


class AssistantValidator:

    def __init__(self, settings: AssistantSettings | None = None):
        self._settings = settings or AssistantSettings()

    async def validate_chat_request(self, request: ChatRequest) -> None:
        if not request.message or not request.message.strip():
            raise ValidationError("Message cannot be empty")

        max_len = self._settings.ASSISTANT_MAX_MESSAGE_LENGTH
        if len(request.message) > max_len:
            raise ValidationError(f"Message exceeds maximum length of {max_len} characters")

        if request.temperature is not None and (request.temperature < 0.0 or request.temperature > 2.0):
            raise ValidationError("Temperature must be between 0.0 and 2.0")

        if request.max_tokens is not None and (request.max_tokens < 1 or request.max_tokens > 16384):
            raise ValidationError("max_tokens must be between 1 and 16384")

        if request.audience and request.audience not in ("patient", "doctor", "nurse", "caregiver", "administrator"):
            raise ValidationError(f"Invalid audience: {request.audience}")

    async def validate_continue_request(self, request: ContinueRequest) -> None:
        if not request.conversation_id:
            raise ValidationError("conversation_id is required for continuation")

        if request.temperature is not None and (request.temperature < 0.0 or request.temperature > 2.0):
            raise ValidationError("Temperature must be between 0.0 and 2.0")

        if request.max_tokens is not None and (request.max_tokens < 1 or request.max_tokens > 16384):
            raise ValidationError("max_tokens must be between 1 and 16384")

        if request.instructions and len(request.instructions) > 1000:
            raise ValidationError("Instructions exceed maximum length of 1000 characters")

    async def validate_explain_request(self, request: ExplainRequest) -> None:
        if not request.term or not request.term.strip():
            raise ValidationError("Term cannot be empty")

        if len(request.term) > 500:
            raise ValidationError("Term exceeds maximum length of 500 characters")

        if request.audience and request.audience not in ("patient", "doctor", "nurse", "caregiver", "administrator"):
            raise ValidationError(f"Invalid audience: {request.audience}")

    def _validate_not_empty(self, value: str, field_name: str) -> None:
        if not value or not value.strip():
            raise ValidationError(f"{field_name} cannot be empty")

    def _validate_max_length(self, value: str, max_len: int, field_name: str) -> None:
        if len(value) > max_len:
            raise ValidationError(f"{field_name} exceeds maximum length of {max_len} characters")

    def _validate_temperature(self, temperature: float | None) -> None:
        if temperature is not None and (temperature < 0.0 or temperature > 2.0):
            raise ValidationError("Temperature must be between 0.0 and 2.0")

    def _validate_max_tokens(self, max_tokens: int | None) -> None:
        if max_tokens is not None and (max_tokens < 1 or max_tokens > 16384):
            raise ValidationError("max_tokens must be between 1 and 16384")

    def _validate_audience(self, audience: str | None) -> None:
        valid = ("patient", "doctor", "nurse", "caregiver", "administrator")
        if audience and audience not in valid:
            raise ValidationError(f"Invalid audience: {audience}")

    async def validate_session_ownership(self, session_id: str, user_id: int) -> bool:
        return True

    async def validate_conversation_continuity(self, conversation_id: str) -> bool:
        return True
