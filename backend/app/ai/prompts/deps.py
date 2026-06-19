from app.ai.prompts.registry import PromptRegistry


_registry: PromptRegistry | None = None


def get_prompt_registry() -> PromptRegistry:
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry


def set_prompt_registry(registry: PromptRegistry) -> None:
    global _registry
    _registry = registry


def reset_prompt_registry() -> None:
    global _registry
    _registry = None
