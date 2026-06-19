import pytest

from app.ai.evidence.exceptions import (
    CitationError,
    ConfidenceError,
    ConflictError,
    CoverageError,
    EvidenceConfigError,
    EvidenceError,
    EvidencePipelineError,
    EvidenceServiceError,
    ExplainabilityError,
    ProvenanceError,
    VerificationError,
)


class TestEvidenceExceptions:
    def test_exception_hierarchy(self):
        assert issubclass(EvidenceError, Exception)
        assert issubclass(VerificationError, EvidenceError)
        assert issubclass(CitationError, EvidenceError)
        assert issubclass(CoverageError, EvidenceError)
        assert issubclass(ConflictError, EvidenceError)
        assert issubclass(ConfidenceError, EvidenceError)
        assert issubclass(ProvenanceError, EvidenceError)
        assert issubclass(ExplainabilityError, EvidenceError)
        assert issubclass(EvidenceConfigError, EvidenceError)
        assert issubclass(EvidencePipelineError, EvidenceError)
        assert issubclass(EvidenceServiceError, EvidenceError)

    def test_exceptions_can_be_raised_and_caught(self):
        for exc_cls in [
            VerificationError,
            CitationError,
            CoverageError,
            ConflictError,
            ConfidenceError,
            ProvenanceError,
            ExplainabilityError,
            EvidenceConfigError,
            EvidencePipelineError,
            EvidenceServiceError,
        ]:
            with pytest.raises(exc_cls):
                raise exc_cls("test error")

    def test_exception_messages(self):
        assert str(VerificationError("custom message")) == "custom message"
        assert str(CitationError("missing source")) == "missing source"
        assert str(CoverageError("insufficient coverage")) == "insufficient coverage"
        assert str(ConflictError("conflict detected")) == "conflict detected"
        assert str(ConfidenceError("low confidence")) == "low confidence"
        assert str(ProvenanceError("provenance missing")) == "provenance missing"
        assert str(ExplainabilityError("no explanation")) == "no explanation"
        assert str(EvidenceConfigError("invalid config")) == "invalid config"
        assert str(EvidencePipelineError("pipeline failed")) == "pipeline failed"
        assert str(EvidenceServiceError("service error")) == "service error"

    def test_isinstance_checks(self):
        exc = EvidenceError("base")
        assert isinstance(exc, EvidenceError)
        assert isinstance(exc, Exception)

        for exc_cls in [
            VerificationError,
            CitationError,
            CoverageError,
            ConflictError,
            ConfidenceError,
            ProvenanceError,
            ExplainabilityError,
            EvidenceConfigError,
            EvidencePipelineError,
            EvidenceServiceError,
        ]:
            instance = exc_cls("test")
            assert isinstance(instance, EvidenceError)
            assert isinstance(instance, exc_cls)

    def test_evidence_error_default_message(self):
        assert str(EvidenceError()) == ""
