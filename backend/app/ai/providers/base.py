from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncGenerator


@dataclass
class ModelInfo:
    name: str
    provider: str
    context_window: int
    supports_streaming: bool
    supports_functions: bool = False


@dataclass
class CompletionResponse:
    content: str
    model: str
    provider: str
    usage: dict | None = None
    finish_reason: str | None = None
    raw: dict | None = field(default=None, compare=False)


class LLMProvider(ABC):

    @abstractmethod
    async def generate(self, messages: list[dict], **kwargs) -> CompletionResponse:
        ...

    @abstractmethod
    async def generate_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        ...

    @abstractmethod
    async def count_tokens(self, messages: list[dict]) -> int:
        ...

    @abstractmethod
    async def get_model_info(self) -> ModelInfo:
        ...
