from app.ai.medical.config.config import MedicalSettings
from app.ai.medical.pipelines.pipelines import MedicalPipeline
from app.ai.medical.services.services import MedicalService

_medical_service: MedicalService | None = None
_medical_pipeline: MedicalPipeline | None = None
_medical_settings: MedicalSettings | None = None


def get_medical_settings() -> MedicalSettings:
    global _medical_settings
    if _medical_settings is None:
        _medical_settings = MedicalSettings()
    return _medical_settings


def get_medical_pipeline() -> MedicalPipeline:
    global _medical_pipeline
    if _medical_pipeline is None:
        _medical_pipeline = MedicalPipeline(
            settings=get_medical_settings(),
        )
    return _medical_pipeline


def get_medical_service() -> MedicalService:
    global _medical_service
    if _medical_service is None:
        _medical_service = MedicalService(
            pipeline=get_medical_pipeline(),
            settings=get_medical_settings(),
        )
    return _medical_service


def set_medical_service(service: MedicalService) -> None:
    global _medical_service
    _medical_service = service


def reset_medical_service() -> None:
    global _medical_service, _medical_pipeline, _medical_settings
    _medical_service = None
    _medical_pipeline = None
    _medical_settings = None
