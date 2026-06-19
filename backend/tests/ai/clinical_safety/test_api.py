import pytest
from pydantic import ValidationError

from app.ai.clinical_safety.api.api import SafetyHealthResponse, SafetyValidateRequest
from app.ai.clinical_safety.schemas import (
    ApprovalDecision,
    ApprovalResult,
    SafetyServiceResult,
)


class TestSafetyValidateRequest:
    def test_request_creation(self):
        request = SafetyValidateRequest(response_text="Take aspirin daily for heart health.")
        assert request.response_text == "Take aspirin daily for heart health."
        assert request.claims is None
        assert request.evidence is None

    def test_request_min_length_enforced(self):
        with pytest.raises(ValidationError):
            SafetyValidateRequest(response_text="")

    def test_request_max_length_enforced(self):
        with pytest.raises(ValidationError):
            SafetyValidateRequest(response_text="a" * 50001)

    def test_request_with_optional_fields(self):
        request = SafetyValidateRequest(
            response_text="Aspirin reduces heart attack risk.",
            claims=["Aspirin reduces heart attack risk"],
            evidence={"Aspirin reduces heart attack risk": "true"},
        )
        assert request.claims == ["Aspirin reduces heart attack risk"]
        assert request.evidence == {"Aspirin reduces heart attack risk": "true"}

    def test_request_with_empty_claims_list(self):
        request = SafetyValidateRequest(
            response_text="Test.",
            claims=[],
        )
        assert request.claims == []

    def test_request_with_empty_evidence_dict(self):
        request = SafetyValidateRequest(
            response_text="Test.",
            evidence={},
        )
        assert request.evidence == {}

    def test_request_serialization(self):
        request = SafetyValidateRequest(response_text="Aspirin reduces risk.")
        data = request.model_dump()
        assert data["response_text"] == "Aspirin reduces risk."
        assert data["claims"] is None
        assert data["evidence"] is None

    def test_request_deserialization(self):
        data = {
            "response_text": "Aspirin reduces heart attack risk.",
            "claims": ["Aspirin reduces heart attack risk"],
        }
        request = SafetyValidateRequest.model_validate(data)
        assert request.response_text == "Aspirin reduces heart attack risk."
        assert request.claims == ["Aspirin reduces heart attack risk"]


class TestSafetyHealthResponse:
    def test_health_response_defaults(self):
        response = SafetyHealthResponse()
        assert response.status == "healthy"
        assert response.service == "clinical_safety"

    def test_health_response_custom_values(self):
        response = SafetyHealthResponse(status="degraded", service="custom_safety")
        assert response.status == "degraded"
        assert response.service == "custom_safety"

    def test_health_response_serialization(self):
        response = SafetyHealthResponse()
        data = response.model_dump()
        assert data["status"] == "healthy"
        assert data["service"] == "clinical_safety"


class TestSafetyServiceResultResponse:
    def test_response_model_creation(self):
        result = SafetyServiceResult(
            passed=True,
            summary="All checks passed.",
            warnings=[],
            errors=[],
            processing_time_ms=12.5,
        )
        assert result.passed is True
        assert result.summary == "All checks passed."
        assert result.processing_time_ms == 12.5

    def test_response_with_approval(self):
        approval = ApprovalResult(
            decision=ApprovalDecision.APPROVED,
            reasons=["All checks passed."],
            warnings=[],
            requires_escalation=False,
            requires_override=False,
            summary="Approved.",
        )
        result = SafetyServiceResult(
            passed=True,
            approval=approval,
            summary="All checks passed.",
            processing_time_ms=10.0,
        )
        assert result.approval is not None
        assert result.approval.decision == ApprovalDecision.APPROVED

    def test_response_with_warnings_and_errors(self):
        result = SafetyServiceResult(
            passed=False,
            summary="Issues found.",
            warnings=["Emergency detected"],
            errors=["Pipeline error"],
            processing_time_ms=5.0,
        )
        assert result.passed is False
        assert "Emergency detected" in result.warnings
        assert "Pipeline error" in result.errors

    def test_response_defaults(self):
        result = SafetyServiceResult()
        assert result.passed is False
        assert result.pipeline_result is None
        assert result.approval is None
        assert result.summary is None
        assert result.warnings == []
        assert result.errors == []
        assert result.processing_time_ms == 0.0


class TestSafetyRouter:
    def test_router_prefix(self):
        from app.ai.clinical_safety.api.api import router
        assert router.prefix == "/ai/safety"

    def test_router_tags(self):
        from app.ai.clinical_safety.api.api import router
        assert "Clinical Safety" in router.tags

    def test_router_has_health_route(self):
        from app.ai.clinical_safety.api.api import router
        routes = [r.path for r in router.routes]
        assert "/ai/safety/health" in routes

    def test_router_has_validate_route(self):
        from app.ai.clinical_safety.api.api import router
        routes = [r.path for r in router.routes]
        assert "/ai/safety/validate" in routes

    def test_router_has_hallucination_route(self):
        from app.ai.clinical_safety.api.api import router
        routes = [r.path for r in router.routes]
        assert "/ai/safety/hallucination" in routes

    def test_router_has_unsupported_route(self):
        from app.ai.clinical_safety.api.api import router
        routes = [r.path for r in router.routes]
        assert "/ai/safety/unsupported" in routes

    def test_router_has_risk_route(self):
        from app.ai.clinical_safety.api.api import router
        routes = [r.path for r in router.routes]
        assert "/ai/safety/risk" in routes

    def test_router_has_emergency_route(self):
        from app.ai.clinical_safety.api.api import router
        routes = [r.path for r in router.routes]
        assert "/ai/safety/emergency" in routes

    def test_router_has_phi_route(self):
        from app.ai.clinical_safety.api.api import router
        routes = [r.path for r in router.routes]
        assert "/ai/safety/phi" in routes

    def test_router_has_disclaimer_route(self):
        from app.ai.clinical_safety.api.api import router
        routes = [r.path for r in router.routes]
        assert "/ai/safety/disclaimer" in routes

    def test_router_has_compliance_route(self):
        from app.ai.clinical_safety.api.api import router
        routes = [r.path for r in router.routes]
        assert "/ai/safety/compliance" in routes

    def test_router_has_approval_route(self):
        from app.ai.clinical_safety.api.api import router
        routes = [r.path for r in router.routes]
        assert "/ai/safety/approval" in routes

    def test_health_route_is_get(self):
        from app.ai.clinical_safety.api.api import router
        for route in router.routes:
            if route.path == "/ai/safety/health":
                assert "GET" in route.methods
                return

    def test_validate_route_is_post(self):
        from app.ai.clinical_safety.api.api import router
        for route in router.routes:
            if route.path == "/ai/safety/validate":
                assert "POST" in route.methods
                return
