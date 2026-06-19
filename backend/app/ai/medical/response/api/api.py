from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.ai.medical.response.deps.deps import get_response_service
from app.ai.medical.response.exceptions.exceptions import ResponseServiceError
from app.ai.medical.response.schemas.schemas import (
    GenerateRequest,
    GenerateRequestSimple,
    GenerateResponse,
    StreamChunk,
)
from app.ai.medical.response.services.services import ResponseService
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai/medical", tags=["Medical Response Generation"])


@router.post(
    "/generate",
    response_model=GenerateResponse,
    summary="Generate structured medical response with reasoning, citations, and formatting",
)
async def generate_response(
    request: GenerateRequest,
    service: ResponseService = Depends(get_response_service),
    current_user: User = Depends(get_current_user),
):
    if request.stream:
        return StreamingResponse(
            _stream_generate(request, service),
            media_type="text/event-stream",
        )
    try:
        return await service.generate(request)
    except ResponseServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/generate/simple",
    response_model=GenerateResponse,
    summary="Simple medical response generation without reasoning plan",
)
async def generate_simple(
    request: GenerateRequestSimple,
    service: ResponseService = Depends(get_response_service),
    current_user: User = Depends(get_current_user),
):
    full_request = GenerateRequest(
        query=request.query,
        conversation_id=request.conversation_id,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        stream=request.stream,
        top_k=request.top_k,
    )

    if full_request.stream:
        return StreamingResponse(
            _stream_generate(full_request, service),
            media_type="text/event-stream",
        )
    try:
        return await service.generate(full_request)
    except ResponseServiceError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/generate/stream",
    response_class=StreamingResponse,
    summary="Streaming medical response generation",
)
async def generate_stream(
    request: GenerateRequest,
    service: ResponseService = Depends(get_response_service),
    current_user: User = Depends(get_current_user),
):
    return StreamingResponse(
        _stream_generate(request, service),
        media_type="text/event-stream",
    )


async def _stream_generate(
    request: GenerateRequest,
    service: ResponseService,
):
    try:
        async for chunk in service.generate_stream(request):
            yield f"data: {chunk.model_dump_json()}\n\n"
    except Exception as e:
        yield f"data: {StreamChunk(content='', done=True, finish_reason='error').model_dump_json()}\n\n"
