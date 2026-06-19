from app.ai.interfaces.memory_manager import MemoryManager, Conversation, Message
from app.ai.exceptions.exceptions import MemoryError, ContextWindowExceeded
from app.ai.utils.token_counter import estimate_tokens, truncate_messages
from app.core.config import settings

import uuid
from datetime import datetime, timezone


class InMemoryMemoryManager(MemoryManager):

    def __init__(self):
        self._conversations: dict[str, Conversation] = {}

    async def create_conversation(self, metadata: dict | None = None) -> Conversation:
        conversation = Conversation(
            id=str(uuid.uuid4()),
            metadata=metadata or {},
        )
        self._conversations[conversation.id] = conversation
        return conversation

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        return self._conversations.get(conversation_id)

    async def add_message(self, conversation_id: str, role: str, content: str, token_count: int = 0, metadata: dict | None = None) -> Message:
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            raise MemoryError(f"Conversation '{conversation_id}' not found")
        if not token_count:
            token_count = estimate_tokens(content)
        message = Message(
            role=role,
            content=content,
            token_count=token_count,
            metadata=metadata,
        )
        conversation.messages.append(message)
        conversation.total_tokens += token_count
        conversation.updated_at = datetime.now(timezone.utc)
        max_tokens = settings.AI.MEMORY_MAX_TOKENS
        if conversation.total_tokens > max_tokens:
            messages_dict = [{"role": m.role, "content": m.content} for m in conversation.messages]
            truncated = truncate_messages(messages_dict, max_tokens)
            conversation.messages = [
                Message(role=m["role"], content=m["content"], token_count=estimate_tokens(m["content"]))
                for m in truncated
            ]
            conversation.total_tokens = sum(m.token_count for m in conversation.messages)
        return message

    async def get_context(self, conversation_id: str, max_tokens: int | None = None) -> list[dict]:
        conversation = self._conversations.get(conversation_id)
        if not conversation:
            raise MemoryError(f"Conversation '{conversation_id}' not found")
        messages = [{"role": m.role, "content": m.content} for m in conversation.messages]
        if max_tokens:
            from app.ai.utils.token_counter import estimate_messages_tokens
            if estimate_messages_tokens(messages) > max_tokens:
                messages = truncate_messages(messages, max_tokens)
        return messages

    async def delete_conversation(self, conversation_id: str) -> bool:
        if conversation_id in self._conversations:
            del self._conversations[conversation_id]
            return True
        return False
