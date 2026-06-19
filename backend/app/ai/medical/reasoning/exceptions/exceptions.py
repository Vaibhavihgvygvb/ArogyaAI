class ReasoningError(Exception):
    pass


class ReasoningPlannerError(ReasoningError):
    pass


class EvidencePlannerError(ReasoningError):
    pass


class RetrievalStrategyError(ReasoningError):
    pass


class ContextRankingError(ReasoningError):
    pass


class ContextCompressionError(ReasoningError):
    pass


class PromptAssemblyError(ReasoningError):
    pass


class CitationPlanningError(ReasoningError):
    pass


class ConfidencePlanningError(ReasoningError):
    pass


class SafetyPlanningError(ReasoningError):
    pass


class ReasoningPipelineError(ReasoningError):
    pass


class ReasoningServiceError(ReasoningError):
    pass
