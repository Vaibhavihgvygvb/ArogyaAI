from app.ai.medical.reasoning.config.config import ReasoningSettings
from app.ai.medical.reasoning.pipelines.pipelines import ReasoningPipeline
from app.ai.medical.reasoning.services.services import ReasoningService

_reasoning_service: ReasoningService | None = None
_reasoning_pipeline: ReasoningPipeline | None = None
_reasoning_settings: ReasoningSettings | None = None


def get_reasoning_settings() -> ReasoningSettings:
    global _reasoning_settings
    if _reasoning_settings is None:
        _reasoning_settings = ReasoningSettings()
    return _reasoning_settings


def get_reasoning_pipeline() -> ReasoningPipeline:
    global _reasoning_pipeline
    if _reasoning_pipeline is None:
        _reasoning_pipeline = ReasoningPipeline(
            settings=get_reasoning_settings(),
        )
    return _reasoning_pipeline


def get_reasoning_service() -> ReasoningService:
    global _reasoning_service
    if _reasoning_service is None:
        _reasoning_service = ReasoningService(
            pipeline=get_reasoning_pipeline(),
            settings=get_reasoning_settings(),
        )
    return _reasoning_service


def set_reasoning_service(service: ReasoningService) -> None:
    global _reasoning_service
    _reasoning_service = service


def set_reasoning_pipeline(pipeline: ReasoningPipeline) -> None:
    global _reasoning_pipeline
    _reasoning_pipeline = pipeline


def reset_reasoning_service() -> None:
    global _reasoning_service, _reasoning_pipeline, _reasoning_settings
    _reasoning_service = None
    _reasoning_pipeline = None
    _reasoning_settings = None
