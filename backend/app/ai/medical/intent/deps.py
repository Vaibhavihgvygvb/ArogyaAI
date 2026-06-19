from app.ai.medical.intent.services import IntentDetectorService
from app.ai.medical.intent.interfaces import IntentServiceABC

_intent_service: IntentServiceABC | None = None


def get_intent_service() -> IntentServiceABC:
    global _intent_service
    if _intent_service is None:
        _intent_service = IntentDetectorService()
    return _intent_service


def set_intent_service(service: IntentServiceABC) -> None:
    global _intent_service
    _intent_service = service


def reset_intent_service() -> None:
    global _intent_service
    _intent_service = None
