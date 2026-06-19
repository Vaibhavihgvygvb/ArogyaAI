from app.ai.medical.response.config.config import ResponseSettings
from app.ai.medical.response.pipelines.pipelines import ResponsePipeline
from app.ai.medical.response.services.services import ResponseService

_response_service: ResponseService | None = None
_response_pipeline: ResponsePipeline | None = None
_response_settings: ResponseSettings | None = None


def get_response_settings() -> ResponseSettings:
    global _response_settings
    if _response_settings is None:
        _response_settings = ResponseSettings()
    return _response_settings


def get_response_pipeline() -> ResponsePipeline:
    global _response_pipeline
    if _response_pipeline is None:
        _response_pipeline = ResponsePipeline(
            settings=get_response_settings(),
        )
    return _response_pipeline


def get_response_service() -> ResponseService:
    global _response_service
    if _response_service is None:
        _response_service = ResponseService(
            pipeline=get_response_pipeline(),
            settings=get_response_settings(),
        )
    return _response_service


def set_response_service(service: ResponseService) -> None:
    global _response_service
    _response_service = service


def set_response_pipeline(pipeline: ResponsePipeline) -> None:
    global _response_pipeline
    _response_pipeline = pipeline


def reset_response_service() -> None:
    global _response_service, _response_pipeline, _response_settings
    _response_service = None
    _response_pipeline = None
    _response_settings = None
