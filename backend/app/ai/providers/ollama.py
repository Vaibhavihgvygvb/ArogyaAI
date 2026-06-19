import json
from typing import AsyncGenerator

import httpx

from app.ai.providers.base import LLMProvider, CompletionResponse, ModelInfo
from app.ai.exceptions.exceptions import ProviderConnectionError, ProviderTimeoutError
from app.core.config import settings


class OllamaProvider(LLMProvider):

    def __init__(self, base_url: str | None = None, model: str | None = None):
        self.base_url = (base_url or settings.AI.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.AI.OLLAMA_MODEL
        self._client = httpx.AsyncClient(timeout=settings.AI.DEFAULT_TIMEOUT_SECONDS)

    async def generate(self, messages: list[dict], **kwargs) -> CompletionResponse:
        payload = self._build_payload(messages, kwargs)
        try:
            response = await self._client.post(
                f"{self.base_url}/api/chat",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return CompletionResponse(
                content=data.get("message", {}).get("content", ""),
                model=data.get("model", self.model),
                provider="ollama",
                usage={"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
                finish_reason="stop",
                raw=data,
            )
        except httpx.ConnectError as e:
            raise ProviderConnectionError(f"Could not connect to Ollama at {self.base_url}") from e
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("Ollama request timed out") from e

    async def generate_stream(self, messages: list[dict], **kwargs) -> AsyncGenerator[str, None]:
        payload = self._build_payload(messages, {**kwargs, "stream": True})
        try:
            async with self._client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            chunk = json.loads(line)
                            content = chunk.get("message", {}).get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except httpx.ConnectError as e:
            raise ProviderConnectionError(f"Could not connect to Ollama at {self.base_url}") from e
        except httpx.TimeoutException as e:
            raise ProviderTimeoutError("Ollama stream request timed out") from e

    async def count_tokens(self, messages: list[dict]) -> int:
        from app.ai.utils.token_counter import estimate_messages_tokens
        return estimate_messages_tokens(messages)

    async def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name=self.model,
            provider="ollama",
            context_window=settings.AI.DEFAULT_CONTEXT_WINDOW,
            supports_streaming=True,
        )

    def _build_payload(self, messages: list[dict], kwargs: dict) -> dict:
        fmt_messages = []
        for m in messages:
            fmt_messages.append({"role": m["role"], "content": m["content"]})
        payload = {
            "model": self.model,
            "messages": fmt_messages,
            "stream": kwargs.get("stream", False),
            "options": {
                "temperature": kwargs.get("temperature", settings.AI.DEFAULT_TEMPERATURE),
                "top_p": kwargs.get("top_p", settings.AI.DEFAULT_TOP_P),
                "num_predict": kwargs.get("max_tokens", settings.AI.DEFAULT_MAX_TOKENS),
            },
        }
        return payload
