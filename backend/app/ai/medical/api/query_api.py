from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.medical.engine.deps import get_query_understanding_engine
from app.ai.medical.engine.interfaces import QueryUnderstandingEngineABC
from app.ai.medical.engine.schemas import (
    AnalyzeRequest,
    AnalyzeResponse,
    AnalysisScope,
    IntentResult,
    EntityResult,
    SpecialtyResult,
    UrgencyResult,
    AudienceResult,
    LanguageInfo,
    RewriteResult,
    QueryUnderstandingResult,
)
from app.api.deps import get_current_user
from app.models.user import User
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ai/medical", tags=["Medical Query Understanding"])


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    summary="Full query understanding analysis — intent, entities, specialty, urgency, audience, language, rewrite",
)
async def analyze_query(
    request: AnalyzeRequest,
    engine: QueryUnderstandingEngineABC = Depends(get_query_understanding_engine),
    current_user: User = Depends(get_current_user),
):
    result = await engine.analyze(
        query=request.query,
        conversation_id=request.conversation_id,
    )
    return AnalyzeResponse(
        result=result,
        query=request.query,
        analysis_time_ms=result.analysis_time_ms,
    )


@router.post(
    "/intent",
    response_model=IntentResult,
    summary="Detect medical intent of a query",
)
async def detect_intent(
    request: QueryRequest,
    engine: QueryUnderstandingEngineABC = Depends(get_query_understanding_engine),
    current_user: User = Depends(get_current_user),
):
    return await engine.detect_intent(request.query)


@router.post(
    "/entities",
    response_model=EntityResult,
    summary="Extract medical entities from a query",
)
async def extract_entities(
    request: QueryRequest,
    engine: QueryUnderstandingEngineABC = Depends(get_query_understanding_engine),
    current_user: User = Depends(get_current_user),
):
    return await engine.extract_entities(request.query)


@router.post(
    "/rewrite",
    response_model=RewriteResult,
    summary="Rewrite query for retrieval",
)
async def rewrite_query(
    request: QueryRequest,
    engine: QueryUnderstandingEngineABC = Depends(get_query_understanding_engine),
    current_user: User = Depends(get_current_user),
):
    return await engine.rewrite_query(request.query)


@router.get(
    "/specialties",
    response_model=list[dict],
    summary="List all supported medical specialties",
)
async def list_specialties(
    current_user: User = Depends(get_current_user),
):
    from app.ai.medical.specialty.services import _SPECIALTY_KEYWORDS
    return [
        {"name": k.replace("_", " ").title(), "value": k, "keyword_count": len(v)}
        for k, v in _SPECIALTY_KEYWORDS.items()
    ]


@router.get(
    "/intents",
    response_model=list[dict],
    summary="List all supported intent categories",
)
async def list_intents(
    current_user: User = Depends(get_current_user),
):
    from app.ai.medical.intent.schemas import INTENT_CATEGORIES
    return [
        {"name": c.name.replace("_", " ").title(), "value": c.name, "description": c.description, "priority": c.priority}
        for c in INTENT_CATEGORIES
    ]
