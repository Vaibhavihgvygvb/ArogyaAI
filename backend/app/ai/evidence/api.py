from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.evidence.di import get_evidence_service
from app.ai.evidence.schemas import (
    CitationStyle,
    EvidenceSpan,
    PipelineResult,
    ServiceResult,
)
from app.ai.evidence.service import EvidenceService
from app.api.deps import get_current_user
from app.models.user import User
from pydantic import BaseModel, Field


class EvidenceRequest(BaseModel):
    spans: list[EvidenceSpan] = Field(..., min_length=1, max_length=50)
    citation_style: CitationStyle = CitationStyle.AMA


class EvidenceHealthResponse(BaseModel):
    status: str = "healthy"
    service: str = "evidence_intelligence"


router = APIRouter(prefix="/ai/evidence", tags=["Evidence Intelligence"])


@router.get(
    "/health",
    response_model=EvidenceHealthResponse,
    summary="Evidence service health check",
)
async def health():
    return EvidenceHealthResponse()


@router.post(
    "/validate",
    response_model=ServiceResult,
    summary="Validate evidence for medical response spans",
)
async def validate_evidence(
    request: EvidenceRequest,
    service: EvidenceService = Depends(get_evidence_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.validate_evidence(
            spans=request.spans,
            citation_style=request.citation_style,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Evidence validation failed: {e}",
        )


@router.post(
    "/verify",
    response_model=PipelineResult,
    summary="Verify evidence spans against knowledge base",
)
async def verify_evidence(
    request: EvidenceRequest,
    service: EvidenceService = Depends(get_evidence_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.verify(spans=request.spans)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {e}",
        )


@router.post(
    "/citations",
    response_model=PipelineResult,
    summary="Generate citations for evidence spans",
)
async def generate_citations(
    request: EvidenceRequest,
    service: EvidenceService = Depends(get_evidence_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.generate_citations(
            spans=request.spans,
            style=request.citation_style,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Citation generation failed: {e}",
        )


@router.post(
    "/coverage",
    response_model=PipelineResult,
    summary="Analyze evidence coverage",
)
async def analyze_coverage(
    request: EvidenceRequest,
    service: EvidenceService = Depends(get_evidence_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.analyze_coverage(spans=request.spans)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Coverage analysis failed: {e}",
        )


@router.post(
    "/conflicts",
    response_model=PipelineResult,
    summary="Detect conflicts in evidence",
)
async def detect_conflicts(
    request: EvidenceRequest,
    service: EvidenceService = Depends(get_evidence_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.detect_conflicts(spans=request.spans)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Conflict detection failed: {e}",
        )


@router.post(
    "/confidence",
    response_model=PipelineResult,
    summary="Calculate confidence scores for evidence",
)
async def calculate_confidence(
    request: EvidenceRequest,
    service: EvidenceService = Depends(get_evidence_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.calculate_confidence(spans=request.spans)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Confidence calculation failed: {e}",
        )


@router.post(
    "/provenance",
    response_model=PipelineResult,
    summary="Track provenance of evidence processing",
)
async def get_provenance(
    request: EvidenceRequest,
    service: EvidenceService = Depends(get_evidence_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.get_provenance(spans=request.spans)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Provenance tracking failed: {e}",
        )


@router.post(
    "/explain",
    response_model=PipelineResult,
    summary="Get explanation of evidence validation results",
)
async def explain_evidence(
    request: EvidenceRequest,
    service: EvidenceService = Depends(get_evidence_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.get_explanation(spans=request.spans)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Explanation failed: {e}",
        )


@router.post(
    "/pipeline",
    response_model=PipelineResult,
    summary="Run full evidence pipeline",
)
async def full_pipeline(
    request: EvidenceRequest,
    service: EvidenceService = Depends(get_evidence_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.full_pipeline(
            spans=request.spans,
            citation_style=request.citation_style,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {e}",
        )
