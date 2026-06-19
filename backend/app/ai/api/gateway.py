from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.ai.models.schemas import (
    GatewayRequest,
    GatewayResponse,
    ConversationCreateSchema,
    ConversationResponse,
    PromptRegisterRequest,
    PromptResponse,
    SafetyCheckRequest,
    SafetyCheckResponse,
    ProviderInfoResponse,
)
from app.ai.gateway.deps import get_gateway
from app.ai.prompts.deps import get_prompt_registry
from app.ai.memory.deps import get_memory_manager
from app.ai.safety.deps import get_safety_service
from app.ai.providers.deps import get_llm_provider
from app.ai.interfaces.gateway_service import GatewayService
from app.ai.interfaces.prompt_manager import PromptManager, PromptTemplate
from app.ai.interfaces.memory_manager import MemoryManager
from app.ai.interfaces.safety_service import SafetyService
from app.ai.interfaces.llm_provider import LLMProvider
from app.ai.exceptions.exceptions import (
    SafetyError,
    PromptNotFoundError,
    PromptValidationError,
    ProviderError,
    GatewayError,
)
from app.api.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/ai", tags=["AI Platform"])


@router.post(
    "/generate",
    response_model=GatewayResponse,
    summary="Generate AI response via gateway pipeline",
    description="Sends messages through the full AI pipeline: prompt builder → memory → provider → safety → formatter",
    responses={
        200: {"description": "AI response generated successfully"},
        400: {"description": "Invalid request"},
        403: {"description": "Safety check failed"},
        503: {"description": "Provider unavailable"},
    },
)
async def generate(
    request: GatewayRequest,
    gateway: GatewayService = Depends(get_gateway),
    current_user: User = Depends(get_current_user),
):
    try:
        result = await gateway.execute(request)
        return result
    except SafetyError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ProviderError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e))
    except GatewayError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post(
    "/prompts",
    response_model=PromptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new prompt template",
    description="Register a prompt template in the Prompt Registry for later use",
)
async def register_prompt(
    request: PromptRegisterRequest,
    registry: PromptManager = Depends(get_prompt_registry),
    current_user: User = Depends(get_current_user),
):
    try:
        prompt = PromptTemplate(
            name=request.name,
            version=request.version,
            system_prompt=request.system_prompt,
            template=request.template,
            variables=request.variables,
            description=request.description,
            tags=request.tags,
            model=request.model,
        )
        await registry.register_prompt(prompt)
        return PromptResponse(
            name=prompt.name,
            version=prompt.version,
            system_prompt=prompt.system_prompt,
            template=prompt.template,
            variables=prompt.variables,
            description=prompt.description,
            tags=prompt.tags,
            model=prompt.model,
        )
    except PromptValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/prompts",
    response_model=list[PromptResponse],
    summary="List all registered prompts",
    description="List all prompt templates with optional tag filter",
)
async def list_prompts(
    tag: str | None = None,
    registry: PromptManager = Depends(get_prompt_registry),
    current_user: User = Depends(get_current_user),
):
    prompts = await registry.list_prompts(tag=tag)
    return [
        PromptResponse(
            name=p.name,
            version=p.version,
            system_prompt=p.system_prompt,
            template=p.template,
            variables=p.variables,
            description=p.description,
            tags=p.tags,
            model=p.model,
        )
        for p in prompts
    ]


@router.get(
    "/prompts/{name}",
    response_model=PromptResponse,
    summary="Get a prompt template by name",
)
async def get_prompt(
    name: str,
    version: str | None = None,
    registry: PromptManager = Depends(get_prompt_registry),
    current_user: User = Depends(get_current_user),
):
    try:
        prompt = await registry.get_prompt(name, version)
        return PromptResponse(
            name=prompt.name,
            version=prompt.version,
            system_prompt=prompt.system_prompt,
            template=prompt.template,
            variables=prompt.variables,
            description=prompt.description,
            tags=prompt.tags,
            model=prompt.model,
        )
    except PromptNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post(
    "/conversations",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation",
)
async def create_conversation(
    request: ConversationCreateSchema | None = None,
    memory: MemoryManager = Depends(get_memory_manager),
    current_user: User = Depends(get_current_user),
):
    conv = await memory.create_conversation(metadata=request.metadata if request else None)
    return ConversationResponse(
        id=conv.id,
        message_count=len(conv.messages),
        total_tokens=conv.total_tokens,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        metadata=conv.metadata,
    )


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation",
)
async def delete_conversation(
    conversation_id: str,
    memory: MemoryManager = Depends(get_memory_manager),
    current_user: User = Depends(get_current_user),
):
    deleted = await memory.delete_conversation(conversation_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")


@router.post(
    "/safety/check",
    response_model=SafetyCheckResponse,
    summary="Check text for safety issues",
    description="Validates input text against safety rules: prompt injection, PHI detection, content moderation",
)
async def check_safety(
    request: SafetyCheckRequest,
    safety: SafetyService = Depends(get_safety_service),
    current_user: User = Depends(get_current_user),
):
    result = await safety.check_safety(request.text)
    return SafetyCheckResponse(
        passed=result.passed,
        score=result.score,
        reason=result.reason,
        details=result.details,
    )


@router.get(
    "/provider",
    response_model=ProviderInfoResponse,
    summary="Get active AI provider info",
    description="Returns information about the currently active LLM provider",
)
async def get_provider_info(
    provider: LLMProvider = Depends(get_llm_provider),
    current_user: User = Depends(get_current_user),
):
    info = await provider.get_model_info()
    return ProviderInfoResponse(
        name=info.provider,
        model=info.name,
        context_window=info.context_window,
        supports_streaming=info.supports_streaming,
        is_active=True,
    )
