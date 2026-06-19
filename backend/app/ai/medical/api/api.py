from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.medical.deps.deps import get_medical_service
from app.ai.medical.exceptions.exceptions import MedicalIntelligenceError
from app.ai.medical.schemas.schemas import (
    MedicalQuery,
    MedicalResponse,
    MedicalSearchRequest,
    MedicalSearchResponse,
)
from app.ai.medical.services.services import MedicalService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai/medical", tags=["Medical Intelligence"])


@router.post(
    "/query",
    response_model=MedicalResponse,
    summary="Medical intelligence query with intent detection, citations, and confidence scoring",
)
async def medical_query(
    request: MedicalQuery,
    service: MedicalService = Depends(get_medical_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.query(request)
    except MedicalIntelligenceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/search",
    response_model=MedicalSearchResponse,
    summary="Medical search with intent detection across knowledge base",
)
async def medical_search(
    request: MedicalSearchRequest,
    service: MedicalService = Depends(get_medical_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.search(request)
    except MedicalIntelligenceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
