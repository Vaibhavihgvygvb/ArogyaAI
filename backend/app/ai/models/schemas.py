from pydantic import BaseModel, Field


class MessageSchema(BaseModel):
    role: str = Field(description="One of: system, user, assistant")
    content: str = Field(min_length=1, description="Message content")
    metadata: dict | None = None


class ConversationCreateSchema(BaseModel):
    metadata: dict | None = None


class ConversationResponse(BaseModel):
    id: str
    message_count: int
    total_tokens: int
    created_at: str
    updated_at: str
    metadata: dict | None = None


class CompletionRequest(BaseModel):
    messages: list[MessageSchema] = Field(min_length=1, description="Conversation messages")
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    conversation_id: str | None = None


class CompletionResponse(BaseModel):
    content: str
    conversation_id: str
    model: str
    provider: str
    usage: dict | None = None
    finish_reason: str | None = None


class GatewayRequest(BaseModel):
    conversation_id: str | None = None
    messages: list[MessageSchema] | None = None
    prompt_name: str | None = None
    prompt_variables: dict | None = None
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None


class GatewayResponse(BaseModel):
    content: str
    conversation_id: str
    model: str
    provider: str
    usage: dict | None = None
    finish_reason: str | None = None


class PromptRegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    version: str = "1.0.0"
    system_prompt: str = ""
    template: str = Field(min_length=1)
    variables: list[str] = Field(default_factory=list)
    description: str = ""
    tags: list[str] | None = None
    model: str | None = None


class PromptResponse(BaseModel):
    name: str
    version: str
    system_prompt: str
    template: str
    variables: list[str]
    description: str
    tags: list[str] | None
    model: str | None


class SafetyCheckRequest(BaseModel):
    text: str = Field(min_length=1)


class SafetyCheckResponse(BaseModel):
    passed: bool
    score: float
    reason: str | None = None
    details: dict | None = None


class ProviderInfoResponse(BaseModel):
    name: str
    model: str
    context_window: int
    supports_streaming: bool
    is_active: bool
