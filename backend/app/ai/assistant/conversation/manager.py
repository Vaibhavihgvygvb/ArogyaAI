import uuid
from datetime import datetime, timezone

from app.ai.assistant.config.config import AssistantSettings
from app.ai.assistant.exceptions.exceptions import ConversationError
from app.ai.assistant.interfaces.interfaces import ConversationManagerABC
from app.ai.assistant.schemas.schemas import (
    AssistantMessage,
    ConversationState,
    ConversationSummary,
    MessageRole,
)
from app.ai.utils.token_counter import estimate_tokens, truncate_messages


class ConversationManager(ConversationManagerABC):

    def __init__(self, settings: AssistantSettings | None = None):
        self._settings = settings or AssistantSettings()
        self._conversations: dict[str, ConversationSummary] = {}
        self._messages: dict[str, list[AssistantMessage]] = {}

    async def create_conversation(self, user_id: int, session_id: str, metadata: dict | None = None) -> str:
        conversation_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        summary = ConversationSummary(
            conversation_id=conversation_id,
            title=f"Conversation {len(self._conversations) + 1}",
            created_at=now,
            updated_at=now,
            metadata={"user_id": user_id, "session_id": session_id, **(metadata or {})},
        )
        self._conversations[conversation_id] = summary
        self._messages[conversation_id] = []
        return conversation_id

    async def get_conversation(self, conversation_id: str) -> ConversationSummary | None:
        return self._conversations.get(conversation_id)

    async def add_message(self, conversation_id: str, role: str, content: str, metadata: dict | None = None) -> AssistantMessage:
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            raise ConversationError(f"Conversation '{conversation_id}' not found")
        token_count = estimate_tokens(content)
        message = AssistantMessage(
            role=MessageRole(role),
            content=content,
            token_count=token_count,
            metadata=metadata or {},
        )
        if conversation_id not in self._messages:
            self._messages[conversation_id] = []
        self._messages[conversation_id].append(message)
        conversation.message_count += 1
        conversation.updated_at = datetime.now(timezone.utc)

        max_messages = self._settings.ASSISTANT_MAX_HISTORY_MESSAGES
        if len(self._messages[conversation_id]) > max_messages:
            self._messages[conversation_id] = self._messages[conversation_id][-max_messages:]

        return message

    async def get_messages(self, conversation_id: str, limit: int | None = None) -> list[AssistantMessage]:
        messages = self._messages.get(conversation_id, [])
        if limit and len(messages) > limit:
            return messages[-limit:]
        return messages

    async def get_context_messages(self, conversation_id: str, max_tokens: int = 2048) -> list[dict]:
        messages = await self.get_messages(conversation_id)
        if not messages:
            return []
        formatted = [
            {"role": m.role.value, "content": m.content}
            for m in messages
        ]
        from app.ai.utils.token_counter import estimate_messages_tokens
        if estimate_messages_tokens(formatted) > max_tokens:
            formatted = truncate_messages(formatted, max_tokens)
        return formatted

    async def update_state(self, conversation_id: str, state: ConversationState) -> bool:
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            return False
        conversation.metadata["state"] = state.value
        conversation.updated_at = datetime.now(timezone.utc)
        return True

    async def delete_conversation(self, conversation_id: str) -> bool:
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            self._messages.pop(conversation_id, None)
            return True
        return False

    async def list_conversations(self, user_id: int) -> list[ConversationSummary]:
        return [
            c for c in self._conversations.values()
            if c.metadata.get("user_id") == user_id
        ]

    async def generate_summary(self, conversation_id: str) -> ConversationSummary:
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            raise ConversationError(f"Conversation '{conversation_id}' not found")
        messages = await self.get_messages(conversation_id)
        user_messages = [m for m in messages if m.role == MessageRole.USER]
        assistant_messages = [m for m in messages if m.role == MessageRole.ASSISTANT]

        if user_messages:
            conversation.title = user_messages[0].content[:80] + ("..." if len(user_messages[0].content) > 80 else "")

        if assistant_messages:
            last_response = assistant_messages[-1].content[:200]
            conversation.summary = last_response
        else:
            conversation.summary = "No responses yet"

        topics = set()
        for msg in user_messages:
            if msg.metadata and "topics" in msg.metadata:
                topics.update(msg.metadata["topics"])
        conversation.topics = list(topics)

        conversation.updated_at = datetime.now(timezone.utc)
        return conversation
