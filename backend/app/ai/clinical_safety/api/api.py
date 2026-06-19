from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.clinical_safety.deps import get_safety_service
from app.ai.clinical_safety.schemas import (
    ApprovalResult,
    ClinicalRiskReport,
    ComplianceReport,
    DisclaimerResult,
    EmergencyReport,
    HallucinationReport,
    PHIValidationReport,
    PipelineResult,
    SafetyServiceResult,
    UnsupportedClaimReport,
)
from app.ai.clinical_safety.services._service import ClinicalSafetyService
from app.api.deps import get_current_user
from app.models.user import User
from pydantic import BaseModel, Field


class SafetyValidateRequest(BaseModel):
    response_text: str = Field(..., min_length=1, max_length=50000)
    claims: list[str] | None = None
    evidence: dict | None = None


class SafetyHealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "clinical_safety"


router = APIRouter(prefix="/ai/safety", tags=["Clinical Safety"])


@router.get(
    "/health",
    response_model=SafetyHealthResponse,
    summary="Clinical Safety service health check",
)
async def health():
    return SafetyHealthResponse()


@router.post(
    "/validate",
    response_model=SafetyServiceResult,
    summary="Run full clinical safety validation on a response",
    description="Validates a response through hallucination detection, unsupported claims, risk, emergency, PHI, disclaimer, compliance, and approval.",
)
async def validate_safety(
    request: SafetyValidateRequest,
    service: ClinicalSafetyService = Depends(get_safety_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.validate(
            response_text=request.response_text,
            claims=request.claims,
            evidence=request.evidence,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Safety validation failed: {e}",
        )


@router.post(
    "/hallucination",
    response_model=HallucinationReport,
    summary="Detect hallucinations in a response",
    description="Detects fabricated medications, diseases, citations, guidelines, statistics, and recommendations without using an LLM.",
)
async def detect_hallucinations(
    request: SafetyValidateRequest,
    service: ClinicalSafetyService = Depends(get_safety_service),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await service.detect_hallucinations(
            text=request.response_text,
            claims=request.claims,
            evidence=request.evidence,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hallucination detection failed: {e}",
        )


@router.post(
    "/unsupported",
    response_model=UnsupportedClaimReport,
    summary="Detect unsupported claims in a response",
)
async def detect_unsupported_claims(
    request: SafetyValidateRequest,
    service: ClinicalSafetyService = Depends(get_safety_service),
    current_user: User = Depends(get_current_user),
):
    try:
        claims = request.claims or []
        result = await service.detect_unsupported_claims(
            claims=claims,
            evidence=request.evidence,
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unsupported claim detection failed: {e}",
        )


@router.post(
    "/risk",
    response_model=ClinicalRiskReport,
    summary="Assess clinical risk level of a response",
)
async def assess_risk(
    request: SafetyValidateRequest,
    service: ClinicalSafetyService = Depends(get_safety_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.assess_risk(
            text=request.response_text,
            claims=request.claims,
            evidence=request.evidence,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Risk assessment failed: {e}",
        )


@router.post(
    "/emergency",
    response_model=EmergencyReport,
    summary="Detect emergency situations in a response",
)
async def detect_emergency(
    request: SafetyValidateRequest,
    service: ClinicalSafetyService = Depends(get_safety_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.detect_emergency(
            text=request.response_text,
            claims=request.claims,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Emergency detection failed: {e}",
        )


@router.post(
    "/phi",
    response_model=PHIValidationReport,
    summary="Validate response for PHI leakage",
)
async def validate_phi(
    request: SafetyValidateRequest,
    service: ClinicalSafetyService = Depends(get_safety_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.validate_phi(text=request.response_text)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PHI validation failed: {e}",
        )


@router.post(
    "/disclaimer",
    response_model=DisclaimerResult,
    summary="Select appropriate medical disclaimers",
)
async def select_disclaimer(
    request: SafetyValidateRequest,
    service: ClinicalSafetyService = Depends(get_safety_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.select_disclaimer(
            text=request.response_text,
            claims=request.claims,
            evidence=request.evidence,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Disclaimer selection failed: {e}",
        )


@router.post(
    "/compliance",
    response_model=ComplianceReport,
    summary="Validate regulatory compliance of a response",
)
async def validate_compliance(
    request: SafetyValidateRequest,
    service: ClinicalSafetyService = Depends(get_safety_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.validate_compliance(
            text=request.response_text,
            claims=request.claims,
            evidence=request.evidence,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Compliance validation failed: {e}",
        )


@router.post(
    "/approval",
    response_model=ApprovalResult,
    summary="Get safety approval decision for a response",
)
async def get_approval(
    request: SafetyValidateRequest,
    service: ClinicalSafetyService = Depends(get_safety_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.get_approval(
            text=request.response_text,
            claims=request.claims,
            evidence=request.evidence,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Approval failed: {e}",
        )
