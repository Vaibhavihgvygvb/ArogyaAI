from app.ai.assistant.config.config import AssistantSettings
from app.ai.assistant.interfaces.interfaces import (
    ContextManagerABC,
    ConversationManagerABC,
    SessionManagerABC,
)
from app.ai.assistant.schemas.schemas import AssistantMessage, SessionMetadata


class ContextManager(ContextManagerABC):

    def __init__(
        self,
        conversation_manager: ConversationManagerABC,
        session_manager: SessionManagerABC,
        settings: AssistantSettings | None = None,
    ):
        self._conversation_manager = conversation_manager
        self._session_manager = session_manager
        self._settings = settings or AssistantSettings()
        self._summaries: dict[str, str] = {}

    async def get_short_term_context(self, conversation_id: str, max_tokens: int = 1024) -> list[dict]:
        return await self._conversation_manager.get_context_messages(conversation_id, max_tokens=max_tokens)

    async def get_long_term_context(self, conversation_id: str, max_tokens: int = 512) -> str | None:
        summary = self._summaries.get(conversation_id)
        if not summary:
            return None
        if len(summary) > max_tokens * 4:
            summary = summary[: max_tokens * 4]
        return summary

    async def get_relevant_history(self, conversation_id: str, current_query: str, max_messages: int = 10) -> list[AssistantMessage]:
        messages = await self._conversation_manager.get_messages(conversation_id)
        if not messages:
            return []

        query_lower = current_query.lower()
        query_words = set(query_lower.split())

        scored = []
        for m in messages:
            score = 0
            msg_lower = m.content.lower()
            for word in query_words:
                if word in msg_lower and len(word) > 3:
                    score += 1
            if m.metadata and m.metadata.get("topics"):
                topic_match = sum(1 for t in m.metadata["topics"] if t.lower() in query_lower)
                score += topic_match * 2
            scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in scored[:max_messages]]

    async def build_medical_context(self, conversation_id: str, session: SessionMetadata) -> str:
        context_parts = []

        long_term = await self.get_long_term_context(conversation_id)
        if long_term:
            context_parts.append(f"[Conversation Summary]: {long_term}")

        short_term = await self.get_short_term_context(conversation_id, max_tokens=768)
        if short_term:
            context_parts.append("[Recent Messages]:")
            for msg in short_term[-4:]:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]
                context_parts.append(f"{role}: {content}")

        if session.active_topic:
            context_parts.append(f"[Active Topic]: {session.active_topic}")
        if session.medical_specialty:
            context_parts.append(f"[Medical Specialty]: {session.medical_specialty}")
        if session.safety_flags:
            context_parts.append(f"[Safety Flags]: {', '.join(session.safety_flags)}")

        return "\n".join(context_parts)

    async def update_context(self, conversation_id: str, message: AssistantMessage) -> None:
        messages = await self._conversation_manager.get_messages(conversation_id)
        total_tokens = sum(m.token_count for m in messages)
        max_summary_tokens = self._settings.ASSISTANT_CONTEXT_SUMMARY_TOKENS
        if total_tokens > max_summary_tokens * 4:
            summary_parts = []
            for m in messages[-10:]:
                content = m.content[:100]
                summary_parts.append(f"{m.role.value}: {content}")
            self._summaries[conversation_id] = "\n".join(summary_parts)
