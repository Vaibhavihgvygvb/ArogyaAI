from typing import AsyncGenerator

import httpx

from app.ai.providers.base import LLMProvider, CompletionResponse, ModelInfo
from app.ai.exceptions.exceptions import ProviderConnectionError, ProviderTimeoutError
from app.core.config import settings


class OpenAIProvider(LLMProvider):

    def __init__(self, api_key: str | None = None, model: str | None = None, base_url: str | None = None):
        self.api_key = api_key or settings.AI.OPENAI_API_KEY
        self.model = model or settings.AI.OPENAI_MODEL
        self.base_url = (base_url or settings.AI.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=settings.AI.DEFAULT_TIMEOUT_SECONDS,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    async def generate(self, messages: list[dict], **kwargs) -> CompletionResponse:
        payload = self._build_payload(messages, kwargs)
        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()
            choice = data["choices"][0]
            usage = data.get("usage", {})
            return CompletionResponse(
                content=choice["message"]["content"] or "",
                model=data.get("model", self.model),
                provider="openai",
                usage={
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                },
                finish_reason=choice.get("finish_reason", "stop"),
                raw=data,
            )
        except httpx.ConnectError as e:
            raise ProviderConnectionError(f"Could not connect to OpenAI at {self.base_url}") from e
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("OpenAI request timed out") from e

    async def generate_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        payload = self._build_payload(messages, {**kwargs, "stream": True})
        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        chunk_data = line[6:]
                        if chunk_data.strip() == "[DONE]":
                            break
                        import json
                        try:
                            chunk = json.loads(chunk_data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError as e:
            raise ProviderConnectionError(f"Could not connect to OpenAI at {self.base_url}") from e
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("OpenAI stream request timed out") from e

    async def count_tokens(self, messages: list[dict]) -> int:
        from app.ai.utils.token_counter import estimate_messages_tokens
        return estimate_messages_tokens(messages)

    async def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name=self.model,
            provider="openai",
            context_window=settings.AI.DEFAULT_CONTEXT_WINDOW,
            supports_streaming=True,
        )

    def _build_payload(self, messages: list[dict], kwargs: dict) -> dict:
        return {
            "model": self.model,
            "messages": messages,
            "stream": kwargs.get("stream", False),
            "temperature": kwargs.get("temperature", settings.AI.DEFAULT_TEMPERATURE),
            "top_p": kwargs.get("top_p", settings.AI.DEFAULT_TOP_P),
            "max_tokens": kwargs.get("max_tokens", settings.AI.DEFAULT_MAX_TOKENS),
        }
