from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.ai.assistant.deps.deps import get_conversation_manager, get_orchestrator, get_session_manager
from app.ai.assistant.exceptions.exceptions import (
    AssistantError,
    OrchestratorError,
    ValidationError,
)
from app.ai.assistant.interfaces.interfaces import (
    AssistantOrchestratorABC,
    ConversationManagerABC,
    SessionManagerABC,
)
from app.ai.assistant.schemas.schemas import (
    ChatRequest,
    ChatResponse,
    ContinueRequest,
    ConversationListItem,
    ConversationState,
    ExplainRequest,
    ExplainResponse,
    HistoryListResponse,
    HistoryRequest,
    HistoryResponse,
    ResetRequest,
    ResetResponse,
    SessionInfo,
    SessionListResponse,
    SummarizeRequest,
    SummarizeResponse,
)
from app.api.deps import get_current_user, require_roles
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter(prefix="/ai/assistant", tags=["Medical Assistant"])


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Send a message to the medical assistant",
    responses={
        200: {"description": "Successful response with assistant message"},
        400: {"description": "Validation error"},
        401: {"description": "Not authenticated"},
        403: {"description": "Access denied"},
        422: {"description": "Validation error"},
    },
)
async def chat(
    request: ChatRequest,
    orchestrator: AssistantOrchestratorABC = Depends(get_orchestrator),
    current_user: User = Depends(get_current_user),
):
    try:
        return await orchestrator.chat(request, current_user.id)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except OrchestratorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AssistantError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/continue",
    response_model=ChatResponse,
    summary="Continue an existing conversation",
)
async def continue_conversation(
    request: ContinueRequest,
    orchestrator: AssistantOrchestratorABC = Depends(get_orchestrator),
    current_user: User = Depends(get_current_user),
):
    try:
        return await orchestrator.continue_conversation(request, current_user.id)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except OrchestratorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AssistantError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/summarize",
    response_model=SummarizeResponse,
    summary="Summarize a conversation",
)
async def summarize_conversation(
    request: SummarizeRequest,
    orchestrator: AssistantOrchestratorABC = Depends(get_orchestrator),
    current_user: User = Depends(get_current_user),
):
    try:
        return await orchestrator.summarize(request)
    except OrchestratorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AssistantError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/explain",
    response_model=ExplainResponse,
    summary="Explain a medical term",
)
async def explain_term(
    request: ExplainRequest,
    orchestrator: AssistantOrchestratorABC = Depends(get_orchestrator),
    current_user: User = Depends(get_current_user),
):
    try:
        return await orchestrator.explain_term(request)
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except OrchestratorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AssistantError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/history",
    response_model=HistoryResponse,
    summary="Get conversation history",
)
async def get_history(
    request: HistoryRequest,
    orchestrator: AssistantOrchestratorABC = Depends(get_orchestrator),
    current_user: User = Depends(get_current_user),
):
    try:
        return await orchestrator.get_history(request)
    except OrchestratorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AssistantError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/reset",
    response_model=ResetResponse,
    summary="Reset a conversation or session",
)
async def reset_conversation(
    request: ResetRequest,
    orchestrator: AssistantOrchestratorABC = Depends(get_orchestrator),
    current_user: User = Depends(get_current_user),
):
    try:
        return await orchestrator.reset(request, current_user.id)
    except OrchestratorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AssistantError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/session/{session_id}",
    response_model=SessionInfo,
    summary="Get session information",
)
async def get_session(
    session_id: str,
    session_manager: SessionManagerABC = Depends(get_session_manager),
    current_user: User = Depends(get_current_user),
):
    session = await session_manager.get_session(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
    if session.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

    state = await session_manager.get_session_state(session_id)
    return SessionInfo(
        session_id=session.session_id,
        user_id=session.user_id,
        active=state.active if state else True,
        conversation_id=session.conversation_id,
        active_topic=session.active_topic,
        medical_specialty=session.medical_specialty,
        turn_count=state.turn_count if state else 0,
        total_tokens_used=state.total_tokens_used if state else 0,
        preferred_language=session.preferred_language,
        preferred_audience=session.preferred_audience,
        safety_flags=session.safety_flags,
        last_activity=session.last_activity,
        created_at=session.created_at,
        expires_at=session.expires_at,
    )


@router.get(
    "/history/{conversation_id}",
    response_model=HistoryResponse,
    summary="Get conversation history by ID",
)
async def get_history_by_id(
    conversation_id: str,
    orchestrator: AssistantOrchestratorABC = Depends(get_orchestrator),
    current_user: User = Depends(get_current_user),
):
    request = HistoryRequest(conversation_id=conversation_id)
    try:
        return await orchestrator.get_history(request)
    except OrchestratorError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AssistantError as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get(
    "/conversations",
    response_model=HistoryListResponse,
    summary="List all conversations for the current user",
)
async def list_conversations(
    conversation_manager: ConversationManagerABC = Depends(get_conversation_manager),
    current_user: User = Depends(get_current_user),
):
    conversations = await conversation_manager.list_conversations(current_user.id)
    items = []
    for c in conversations:
        state_str = c.metadata.get("state", ConversationState.ACTIVE.value)
        items.append(ConversationListItem(
            conversation_id=c.conversation_id,
            title=c.title,
            summary=c.summary,
            message_count=c.message_count,
            state=ConversationState(state_str) if hasattr(ConversationState, state_str.upper()) else ConversationState.ACTIVE,
            topics=c.topics,
            has_emergency=c.has_emergency,
            created_at=c.created_at,
            updated_at=c.updated_at,
            metadata=c.metadata,
        ))
    return HistoryListResponse(
        conversations=items,
        total=len(items),
    )


