class EvidenceError(Exception):
    pass


class VerificationError(EvidenceError):
    pass


class CitationError(EvidenceError):
    pass


class CoverageError(EvidenceError):
    pass


class ConflictError(EvidenceError):
    pass


class ConfidenceError(EvidenceError):
    pass


class ProvenanceError(EvidenceError):
    pass


class ExplainabilityError(EvidenceError):
    pass


class EvidenceConfigError(EvidenceError):
    pass


class EvidencePipelineError(EvidenceError):
    pass


class EvidenceServiceError(EvidenceError):
    pass
