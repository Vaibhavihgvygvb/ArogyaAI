from app.ai.interfaces.safety_service import SafetyService
from app.ai.safety.service import DefaultSafetyService


_service: SafetyService | None = None


def get_safety_service() -> SafetyService:
    global _service
    if _service is None:
        _service = DefaultSafetyService()
    return _service


def set_safety_service(service: SafetyService) -> None:
    global _service
    _service = service


def reset_safety_service() -> None:
    global _service
    _service = None
