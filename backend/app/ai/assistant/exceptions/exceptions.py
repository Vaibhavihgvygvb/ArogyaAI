class AssistantError(Exception):
    pass


class ConversationError(AssistantError):
    pass


class SessionError(AssistantError):
    pass


class ContextError(AssistantError):
    pass


class OrchestratorError(AssistantError):
    pass


class PersonalizationError(AssistantError):
    pass


class ValidationError(AssistantError):
    pass


class ResponseFormattingError(AssistantError):
    pass


class EmergencyEscalationError(AssistantError):
    pass


class SafetyOverrideError(AssistantError):
    pass
