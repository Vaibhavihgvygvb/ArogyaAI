from typing import AsyncGenerator

from app.ai.providers.base import LLMProvider, CompletionResponse, ModelInfo


class MockLLMProvider(LLMProvider):

    def __init__(self, response: str = "Mock response", model: str = "mock-model"):
        self._response = response
        self._model = model

    async def generate(self, messages: list[dict], **kwargs) -> CompletionResponse:
        return CompletionResponse(
            content=self._response,
            model=self._model,
            provider="mock",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            finish_reason="stop",
        )

    async def generate_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        for word in self._response.split(" "):
            yield word + " "

    async def count_tokens(self, messages: list[dict]) -> int:
        return 10

    async def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name=self._model,
            provider="mock",
            context_window=4096,
            supports_streaming=True,
        )
