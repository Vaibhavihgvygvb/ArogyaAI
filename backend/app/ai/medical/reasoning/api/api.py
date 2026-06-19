from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.medical.engine.deps import get_query_understanding_engine
from app.ai.medical.engine.interfaces import QueryUnderstandingEngineABC
from app.ai.medical.engine.schemas import AnalyzeRequest, AnalyzeResponse
from app.ai.medical.reasoning.deps.deps import get_reasoning_service
from app.ai.medical.reasoning.exceptions.exceptions import ReasoningServiceError
from app.ai.medical.reasoning.schemas.schemas import (
    ReasoningApproach,
    ReasoningRequest,
    ReasoningResponse,
)
from app.ai.medical.reasoning.services.services import ReasoningService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai/medical", tags=["Medical Reasoning"])


@router.post(
    "/reason",
    response_model=ReasoningResponse,
    summary="Full medical reasoning pipeline — plan, retrieve, rank, compress, assemble, cite, estimate confidence, plan safety",
)
async def medical_reason(
    request: ReasoningRequest,
    service: ReasoningService = Depends(get_reasoning_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.reason(
            query=request.original_query,
            conversation_id=request.conversation_id,
            approach_hint=request.approach_hint.value if request.approach_hint else None,
            top_k=request.top_k,
            filters=request.filters,
            min_score=request.min_score,
            max_context_tokens=request.max_context_tokens,
            include_reasoning_plan=request.include_reasoning_plan,
            include_evidence_plan=request.include_evidence_plan,
            include_retrieval_plan=request.include_retrieval_plan,
            include_context_ranking=request.include_context_ranking,
            include_context_compression=request.include_context_compression,
            include_prompt_assembly=request.include_prompt_assembly,
            include_citation_plan=request.include_citation_plan,
            include_confidence_plan=request.include_confidence_plan,
            include_safety_plan=request.include_safety_plan,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
        )
    except ReasoningServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/reason/analyze",
    response_model=ReasoningResponse,
    summary="Analyze query then run full reasoning pipeline — combines analyze + reason",
)
async def reason_with_analysis(
    request: AnalyzeRequest,
    service: ReasoningService = Depends(get_reasoning_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.reason(
            query=request.query,
            conversation_id=request.conversation_id,
            top_k=15,
        )
    except ReasoningServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/reason/approaches",
    response_model=list[dict],
    summary="List all supported reasoning approaches",
)
async def list_reasoning_approaches(
    current_user: User = Depends(get_current_user),
):
    return [
        {
            "name": a.value.replace("_", " ").title(),
            "value": a.value,
            "description": _APPROACH_DESCRIPTIONS.get(a.value, ""),
        }
        for a in ReasoningApproach
    ]


_APPROACH_DESCRIPTIONS: dict[str, str] = {
    "clinical_reasoning": "Systematic clinical evaluation of symptoms, history, and risk factors with differential considerations",
    "evidence_synthesis": "Multi-source evidence aggregation with quality and recency evaluation",
    "comparative_analysis": "Balanced comparison of treatment options, conditions, or interventions",
    "differential_diagnosis": "Structured differential diagnosis building with likelihood ranking",
    "treatment_planning": "Evidence-based treatment approach with monitoring and follow-up parameters",
    "risk_assessment": "Risk factor identification with severity evaluation and preventive recommendations",
    "contextual_information": "Clear contextual medical information with terminology explanation",
    "general_answer": "Well-organized general medical information with appropriate disclaimers",
}
