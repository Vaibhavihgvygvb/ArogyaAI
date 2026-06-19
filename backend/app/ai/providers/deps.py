from app.ai.providers.base import LLMProvider
from app.ai.providers.ollama import OllamaProvider
from app.ai.providers.openai import OpenAIProvider
from app.ai.exceptions.exceptions import ProviderNotFoundError
from app.core.config import settings


_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is not None:
        return _provider
    _provider = _create_provider(settings.AI.ACTIVE_PROVIDER)
    return _provider


def set_llm_provider(provider: LLMProvider) -> None:
    global _provider
    _provider = provider


def reset_llm_provider() -> None:
    global _provider
    _provider = None


def _create_provider(provider_name: str) -> LLMProvider:
    if provider_name == "ollama":
        return OllamaProvider()
    if provider_name == "openai":
        return OpenAIProvider()
    raise ProviderNotFoundError(f"Unknown provider: {provider_name}")
