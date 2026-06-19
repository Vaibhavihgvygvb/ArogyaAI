from app.ai.vector.providers.memory import MemoryVectorStore
from app.ai.vector.services.services import VectorService
from app.core.config import settings

_vector_service: VectorService | None = None


def get_vector_service() -> VectorService:
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService(
            store=MemoryVectorStore(),
        )
    return _vector_service


def set_vector_service(service: VectorService) -> None:
    global _vector_service
    _vector_service = service


def reset_vector_service() -> None:
    global _vector_service
    _vector_service = None
