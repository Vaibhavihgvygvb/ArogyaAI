import pytest
from pydantic import ValidationError

from app.ai.evidence.api import EvidenceHealthResponse, EvidenceRequest
from app.ai.evidence.schemas import CitationStyle, EvidenceSpan


class TestEvidenceRequest:
    def test_evidence_request_creation(self):
        span = EvidenceSpan(text="Aspirin reduces risk", claim="Aspirin reduces heart attack risk")
        request = EvidenceRequest(spans=[span])

        assert len(request.spans) == 1
        assert request.spans[0].claim == "Aspirin reduces heart attack risk"
        assert request.citation_style == CitationStyle.AMA

    def test_evidence_request_with_custom_style(self):
        span = EvidenceSpan(text="Test", claim="Test")
        request = EvidenceRequest(spans=[span], citation_style=CitationStyle.APA)

        assert request.citation_style == CitationStyle.APA

    def test_evidence_request_min_length_enforced(self):
        with pytest.raises(ValidationError):
            EvidenceRequest(spans=[])

    def test_evidence_request_with_multiple_spans(self):
        spans = [
            EvidenceSpan(text="Claim 1", claim="Claim 1"),
            EvidenceSpan(text="Claim 2", claim="Claim 2"),
            EvidenceSpan(text="Claim 3", claim="Claim 3"),
        ]
        request = EvidenceRequest(spans=spans, citation_style=CitationStyle.IEEE)

        assert len(request.spans) == 3
        assert request.citation_style == CitationStyle.IEEE

    def test_evidence_request_with_full_span_data(self):
        span = EvidenceSpan(
            text="Clinical trial shows efficacy",
            claim="Drug X reduces mortality",
            span_start=0,
            span_end=32,
            context="In a randomized controlled trial...",
            metadata={"source": "NEJM", "year": 2024},
        )
        request = EvidenceRequest(spans=[span])

        assert request.spans[0].span_start == 0
        assert request.spans[0].span_end == 32
        assert request.spans[0].context == "In a randomized controlled trial..."
        assert request.spans[0].metadata["source"] == "NEJM"


class TestEvidenceHealthResponse:
    def test_health_response_defaults(self):
        response = EvidenceHealthResponse()

        assert response.status == "healthy"
        assert response.service == "evidence_intelligence"

    def test_health_response_custom_values(self):
        response = EvidenceHealthResponse(status="degraded", service="custom_service")

        assert response.status == "degraded"
        assert response.service == "custom_service"

    def test_health_response_serialization(self):
        response = EvidenceHealthResponse()
        data = response.model_dump()

        assert data["status"] == "healthy"
        assert data["service"] == "evidence_intelligence"
