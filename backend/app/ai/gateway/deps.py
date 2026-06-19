from app.ai.gateway.pipeline import GatewayPipeline
from app.ai.providers.deps import get_llm_provider
from app.ai.prompts.deps import get_prompt_registry
from app.ai.memory.deps import get_memory_manager
from app.ai.safety.deps import get_safety_service
from app.ai.interfaces.gateway_service import GatewayService


_pipeline: GatewayService | None = None


def get_gateway() -> GatewayService:
    global _pipeline
    if _pipeline is None:
        _pipeline = GatewayPipeline(
            provider=get_llm_provider(),
            prompt_manager=get_prompt_registry(),
            memory_manager=get_memory_manager(),
            safety_service=get_safety_service(),
        )
    return _pipeline


def set_gateway(gateway: GatewayService) -> None:
    global _pipeline
    _pipeline = gateway


def reset_gateway() -> None:
    global _pipeline
    _pipeline = None
