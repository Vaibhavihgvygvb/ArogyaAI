from abc import ABC, abstractmethod

from app.ai.assistant.schemas.schemas import (
    AssistantMessage,
    ChatRequest,
    ChatResponse,
    ContinueRequest,
    ConversationState,
    ConversationSummary,
    ExplainRequest,
    ExplainResponse,
    HistoryRequest,
    HistoryResponse,
    PersonalizationPreferences,
    ResetRequest,
    ResetResponse,
    SessionMetadata,
    SessionState,
    SummarizeRequest,
    SummarizeResponse,
)


class ConversationManagerABC(ABC):

    @abstractmethod
    async def create_conversation(self, user_id: int, session_id: str, metadata: dict | None = None) -> str:
        ...

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> ConversationSummary | None:
        ...

    @abstractmethod
    async def add_message(self, conversation_id: str, role: str, content: str, metadata: dict | None = None) -> AssistantMessage:
        ...

    @abstractmethod
    async def get_messages(self, conversation_id: str, limit: int | None = None) -> list[AssistantMessage]:
        ...

    @abstractmethod
    async def get_context_messages(self, conversation_id: str, max_tokens: int = 2048) -> list[dict]:
        ...

    @abstractmethod
    async def update_state(self, conversation_id: str, state: ConversationState) -> bool:
        ...

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        ...

    @abstractmethod
    async def list_conversations(self, user_id: int) -> list[ConversationSummary]:
        ...

    @abstractmethod
    async def generate_summary(self, conversation_id: str) -> ConversationSummary:
        ...


class SessionManagerABC(ABC):

    @abstractmethod
    async def create_session(self, user_id: int, metadata: dict | None = None) -> SessionMetadata:
        ...

    @abstractmethod
    async def get_session(self, session_id: str) -> SessionMetadata | None:
        ...

    @abstractmethod
    async def update_session(self, session_id: str, updates: dict) -> bool:
        ...

    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        ...

    @abstractmethod
    async def list_sessions(self, user_id: int) -> list[SessionMetadata]:
        ...

    @abstractmethod
    async def get_session_state(self, session_id: str) -> SessionState | None:
        ...

    @abstractmethod
    async def touch_session(self, session_id: str) -> bool:
        ...


class ContextManagerABC(ABC):

    @abstractmethod
    async def get_short_term_context(self, conversation_id: str, max_tokens: int = 1024) -> list[dict]:
        ...

    @abstractmethod
    async def get_long_term_context(self, conversation_id: str, max_tokens: int = 512) -> str | None:
        ...

    @abstractmethod
    async def get_relevant_history(self, conversation_id: str, current_query: str, max_messages: int = 10) -> list[AssistantMessage]:
        ...

    @abstractmethod
    async def build_medical_context(self, conversation_id: str, session: SessionMetadata) -> str:
        ...

    @abstractmethod
    async def update_context(self, conversation_id: str, message: AssistantMessage) -> None:
        ...


class PersonalizationManagerABC(ABC):

    @abstractmethod
    async def get_preferences(self, session_id: str) -> PersonalizationPreferences:
        ...

    @abstractmethod
    async def set_preferences(self, session_id: str, preferences: PersonalizationPreferences) -> None:
        ...

    @abstractmethod
    async def update_preferences(self, session_id: str, updates: dict) -> PersonalizationPreferences:
        ...

    @abstractmethod
    async def apply_personalization(self, session_id: str, response: str) -> str:
        ...

    @abstractmethod
    async def personalize_query(self, session_id: str, query: str) -> str:
        ...


class ResponseFormatterABC(ABC):

    @abstractmethod
    async def format_chat_response(self, response: ChatResponse, preferences: PersonalizationPreferences | None = None) -> str:
        ...

    @abstractmethod
    async def format_markdown(self, text: str, audience: str = "patient") -> str:
        ...

    @abstractmethod
    async def extract_key_takeaways(self, text: str, max_items: int = 5) -> list[str]:
        ...

    @abstractmethod
    async def generate_follow_up_questions(self, text: str, max_questions: int = 3) -> list[str]:
        ...

    @abstractmethod
    async def generate_recommended_actions(self, text: str, max_actions: int = 3) -> list[str]:
        ...

    @abstractmethod
    async def simplify_for_audience(self, text: str, audience: str) -> str:
        ...


class AssistantOrchestratorABC(ABC):

    @abstractmethod
    async def chat(self, request: ChatRequest, user_id: int) -> ChatResponse:
        ...

    @abstractmethod
    async def continue_conversation(self, request: ContinueRequest, user_id: int) -> ChatResponse:
        ...

    @abstractmethod
    async def summarize(self, request) -> SummarizeResponse:
        ...

    @abstractmethod
    async def explain_term(self, request: ExplainRequest) -> ExplainResponse:
        ...

    @abstractmethod
    async def get_history(self, request) -> HistoryResponse:
        ...

    @abstractmethod
    async def reset(self, request: ResetRequest, user_id: int) -> ResetResponse:
        ...
