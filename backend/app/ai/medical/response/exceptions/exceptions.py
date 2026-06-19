class ResponseGenerationError(Exception):
    pass


class PromptCompositionError(ResponseGenerationError):
    pass


class StructuredResponseError(ResponseGenerationError):
    pass


class ResponseOrchestrationError(ResponseGenerationError):
    pass


class ResponsePipelineError(ResponseGenerationError):
    pass


class ResponseServiceError(ResponseGenerationError):
    pass


class ResponseBuilderError(ResponseGenerationError):
    pass


class StreamingError(ResponseGenerationError):
    pass
