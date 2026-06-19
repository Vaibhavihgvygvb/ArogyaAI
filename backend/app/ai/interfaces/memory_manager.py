from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Message:
    role: str
    content: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    token_count: int = 0
    metadata: dict | None = None


@dataclass
class Conversation:
    id: str
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict | None = None
    total_tokens: int = 0


class MemoryManager(ABC):

    @abstractmethod
    async def create_conversation(self, metadata: dict | None = None) -> Conversation:
        ...

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        ...

    @abstractmethod
    async def add_message(self, conversation_id: str, role: str, content: str, token_count: int = 0, metadata: dict | None = None) -> Message:
        ...

    @abstractmethod
    async def get_context(self, conversation_id: str, max_tokens: int | None = None) -> list[dict]:
        ...

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> bool:
        ...
