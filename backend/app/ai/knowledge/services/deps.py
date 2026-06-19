from functools import lru_cache

from app.ai.knowledge.catalog.catalog import KnowledgeCatalog
from app.ai.knowledge.services.services import KnowledgeService
from app.ai.knowledge.storage.storage import LocalFileStorage
from app.core.config import settings

_knowledge_service: KnowledgeService | None = None


def get_knowledge_service() -> KnowledgeService:
    global _knowledge_service
    if _knowledge_service is None:
        base_path = settings.AI.KNOWLEDGE_STORAGE_PATH
        catalog_path = settings.AI.KNOWLEDGE_CATALOG_PATH
        storage = LocalFileStorage(base_path=base_path)
        catalog = KnowledgeCatalog(catalog_path=catalog_path)
        _knowledge_service = KnowledgeService(storage=storage, catalog=catalog)
    return _knowledge_service


def set_knowledge_service(service: KnowledgeService) -> None:
    global _knowledge_service
    _knowledge_service = service


def reset_knowledge_service() -> None:
    global _knowledge_service
    _knowledge_service = None
