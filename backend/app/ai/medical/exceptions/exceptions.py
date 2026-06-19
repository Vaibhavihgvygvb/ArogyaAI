class MedicalIntelligenceError(Exception):
    pass


class IntentDetectionError(MedicalIntelligenceError):
    pass


class QueryRewriteError(MedicalIntelligenceError):
    pass


class RetrievalOrchestrationError(MedicalIntelligenceError):
    pass


class ContextOptimizationError(MedicalIntelligenceError):
    pass


class MedicalPromptError(MedicalIntelligenceError):
    pass


class MedicalReasoningError(MedicalIntelligenceError):
    pass


class CitationError(MedicalIntelligenceError):
    pass


class ConfidenceError(MedicalIntelligenceError):
    pass


class SafetyValidationError(MedicalIntelligenceError):
    pass


class ResponseBuilderError(MedicalIntelligenceError):
    pass


class SpecialtyFilterError(MedicalIntelligenceError):
    pass
