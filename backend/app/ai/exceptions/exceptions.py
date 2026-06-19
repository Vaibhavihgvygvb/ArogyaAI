class AIError(Exception):
    pass


class ProviderError(AIError):
    pass


class ProviderNotFoundError(ProviderError):
    pass


class ProviderTimeoutError(ProviderError):
    pass


class ProviderConnectionError(ProviderError):
    pass


class PromptError(AIError):
    pass


class PromptNotFoundError(PromptError):
    pass


class PromptValidationError(PromptError):
    pass


class MemoryError(AIError):
    pass


class ContextWindowExceeded(MemoryError):
    pass


class SafetyError(AIError):
    pass


class InputValidationError(SafetyError):
    pass


class PromptInjectionDetected(SafetyError):
    pass


class PHIDetected(SafetyError):
    pass


class OutputValidationError(SafetyError):
    pass


class GatewayError(AIError):
    pass


class ConfigurationError(AIError):
    pass
