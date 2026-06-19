from fastapi import APIRouter, Depends, HTTPException, status

from app.ai.retrieval.deps.deps import get_retrieval_service
from app.ai.retrieval.exceptions.exceptions import RetrievalError
from app.ai.retrieval.schemas.schemas import RAGRequest, RAGResponse, SearchRequest, SearchResponse
from app.ai.retrieval.services.services import RetrievalService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai/retrieval", tags=["Retrieval Engine"])


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Semantic search across knowledge base",
)
async def search_knowledge(
    request: SearchRequest,
    service: RetrievalService = Depends(get_retrieval_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.search(request)
    except RetrievalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/rag",
    response_model=RAGResponse,
    summary="Retrieval-Augmented Generation: query with context-aware answer",
)
async def rag_generate(
    request: RAGRequest,
    service: RetrievalService = Depends(get_retrieval_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.rag_generate(request)
    except RetrievalError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
