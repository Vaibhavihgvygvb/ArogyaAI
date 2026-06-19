from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationState(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    RESUMED = "resumed"
    COMPLETED = "completed"
    EXPIRED = "expired"
    ESCALATED = "escalated"


class AssistantMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    token_count: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConversationSummary(BaseModel):
    conversation_id: str
    title: str = ""
    summary: str = ""
    message_count: int = 0
    topics: list[str] = Field(default_factory=list)
    specialties: list[str] = Field(default_factory=list)
    intent: str | None = None
    has_emergency: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionMetadata(BaseModel):
    session_id: str
    user_id: int
    conversation_id: str | None = None
    active_topic: str | None = None
    medical_specialty: str | None = None
    context_state: dict[str, Any] = Field(default_factory=dict)
    preferred_language: str = "en"
    preferred_audience: str = "patient"
    literacy_level: str = "standard"
    communication_style: str = "standard"
    accessibility_mode: str = "none"
    safety_flags: list[str] = Field(default_factory=list)
    last_activity: datetime = Field(default_factory=datetime.utcnow)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime | None = None


class SessionState(BaseModel):
    session: SessionMetadata
    active: bool = True
    turn_count: int = 0
    total_tokens_used: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)


class PersonalizationPreferences(BaseModel):
    language: str = "en"
    audience: str = "patient"
    literacy_level: str = "standard"
    communication_style: str = "standard"
    response_length: str = "standard"
    accessibility_mode: str = "none"
    include_citations: bool = True
    include_disclaimers: bool = True
    simplify_terms: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    conversation_id: str | None = Field(None, description="Existing conversation ID")
    session_id: str | None = Field(None, description="Existing session ID")
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=16384)
    stream: bool = False
    audience: str | None = Field(None, description="Override audience: patient, doctor, nurse, caregiver")
    language: str | None = None


class ChatResponse(BaseModel):
    conversation_id: str
    session_id: str
    message: str
    formatted_response: str | None = None
    role: str = "assistant"
    topics: list[str] = Field(default_factory=list)
    intent: str | None = None
    specialty: str | None = None
    citations: list[dict[str, Any]] = Field(default_factory=list)
    disclaimers: list[str] = Field(default_factory=list)
    key_takeaways: list[str] = Field(default_factory=list)
    follow_up_questions: list[str] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    has_emergency: bool = False
    emergency_message: str | None = None
    requires_escalation: bool = False
    processing_time_ms: float = 0.0
    safety_passed: bool = True
    safety_warnings: list[str] = Field(default_factory=list)


class ContinueRequest(BaseModel):
    conversation_id: str = Field(..., description="Existing conversation ID")
    session_id: str | None = None
    instructions: str | None = Field(None, max_length=1000, description="Optional instructions for continuation")
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    max_tokens: int | None = Field(None, ge=1, le=16384)


class SummarizeRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID to summarize")


class SummarizeResponse(BaseModel):
    conversation_id: str
    summary: str
    title: str
    message_count: int
    topics: list[str] = Field(default_factory=list)
    specialties: list[str] = Field(default_factory=list)
    key_points: list[str] = Field(default_factory=list)
    has_emergency: bool = False
    processing_time_ms: float = 0.0


class ExplainRequest(BaseModel):
    conversation_id: str
    term: str = Field(..., min_length=1, max_length=500, description="Medical term to explain")
    audience: str | None = None
    session_id: str | None = None


class ExplainResponse(BaseModel):
    term: str
    plain_english: str
    clinical_definition: str | None = None
    context: str | None = None
    related_terms: list[str] = Field(default_factory=list)
    audience: str = "patient"
    citations: list[dict[str, Any]] = Field(default_factory=list)
    processing_time_ms: float = 0.0


class HistoryRequest(BaseModel):
    conversation_id: str = Field(..., description="Conversation ID")


class HistoryResponse(BaseModel):
    conversation_id: str
    messages: list[AssistantMessage] = Field(default_factory=list)
    summary: ConversationSummary | None = None
    total_messages: int = 0
    total_tokens: int = 0
    processing_time_ms: float = 0.0


class ResetRequest(BaseModel):
    conversation_id: str | None = Field(None, description="Specific conversation to reset")
    session_id: str | None = Field(None, description="Session to reset")


class ResetResponse(BaseModel):
    session_id: str | None = None
    new_conversation_id: str | None = None
    previous_conversation_reset: bool = False
    previous_session_reset: bool = False
    message: str = "Conversation reset successfully"


class SessionInfo(BaseModel):
    session_id: str
    user_id: int
    active: bool
    conversation_id: str | None = None
    active_topic: str | None = None
    medical_specialty: str | None = None
    turn_count: int = 0
    total_tokens_used: int = 0
    preferred_language: str = "en"
    preferred_audience: str = "patient"
    safety_flags: list[str] = Field(default_factory=list)
    last_activity: datetime | None = None
    created_at: datetime | None = None
    expires_at: datetime | None = None


class SessionListResponse(BaseModel):
    sessions: list[SessionInfo] = Field(default_factory=list)
    total: int = 0


class ConversationListItem(BaseModel):
    conversation_id: str
    title: str = ""
    summary: str = ""
    message_count: int = 0
    state: ConversationState = ConversationState.ACTIVE
    topics: list[str] = Field(default_factory=list)
    has_emergency: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class HistoryListResponse(BaseModel):
    conversations: list[ConversationListItem] = Field(default_factory=list)
    total: int = 0
    processing_time_ms: float = 0.0
