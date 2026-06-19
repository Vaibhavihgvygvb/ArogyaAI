from abc import ABC, abstractmethod
from typing import AsyncGenerator

from app.ai.medical.response.schemas.schemas import (
    ClinicalSection,
    GenerateRequest,
    GenerateResponse,
    ResponseMetadata,
    StreamChunk,
    StructuredAnswer,
)
from app.ai.medical.reasoning.schemas.schemas import ReasoningPlan


class PromptCompositionEngineABC(ABC):
    @abstractmethod
    async def compose(
        self,
        query: str,
        reasoning_plan: ReasoningPlan | None = None,
        assembled_prompt: dict | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        conversation_id: str | None = None,
    ) -> dict:
        ...


class StructuredResponseBuilderABC(ABC):
    @abstractmethod
    async def build(
        self,
        raw_content: str,
        reasoning_plan: ReasoningPlan | None = None,
        query: str = "",
        conversation_id: str | None = None,
    ) -> GenerateResponse:
        ...


class ResponseOrchestratorABC(ABC):
    @abstractmethod
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        ...

    @abstractmethod
    async def generate_stream(
        self,
        request: GenerateRequest,
    ) -> AsyncGenerator[StreamChunk, None]:
        ...


class ResponsePipelineABC(ABC):
    @abstractmethod
    async def run(self, request: GenerateRequest) -> GenerateResponse:
        ...

    @abstractmethod
    async def run_stream(
        self,
        request: GenerateRequest,
    ) -> AsyncGenerator[StreamChunk, None]:
        ...


class ResponseServiceABC(ABC):
    @abstractmethod
    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        ...

    @abstractmethod
    async def generate_stream(
        self,
        request: GenerateRequest,
    ) -> AsyncGenerator[StreamChunk, None]:
        ...
