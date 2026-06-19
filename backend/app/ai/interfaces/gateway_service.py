from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncGenerator


@dataclass
class GatewayRequest:
    conversation_id: str | None = None
    messages: list[dict] | None = None
    prompt_name: str | None = None
    prompt_variables: dict | None = None
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass
class GatewayResponse:
    content: str
    conversation_id: str
    model: str
    provider: str
    usage: dict | None = None
    finish_reason: str | None = None


class GatewayService(ABC):

    @abstractmethod
    async def execute(self, request: GatewayRequest) -> GatewayResponse:
        ...

    @abstractmethod
    async def execute_stream(self, request: GatewayRequest) -> AsyncGenerator[str, None]:
        ...
