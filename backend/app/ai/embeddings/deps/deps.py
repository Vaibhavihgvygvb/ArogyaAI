from app.ai.embeddings.batch.batch import BatchProcessor
from app.ai.embeddings.cache.cache import MemoryEmbeddingCache
from app.ai.embeddings.pipelines.pipelines import DefaultEmbeddingPipeline
from app.ai.embeddings.services.services import EmbeddingService
from app.ai.embeddings.storage.storage import LocalEmbeddingStorage
from app.core.config import settings

_embedding_service: EmbeddingService | None = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        base_path = settings.AI.KNOWLEDGE_STORAGE_PATH.replace("documents", "embeddings")
        storage = LocalEmbeddingStorage(base_path=base_path)
        pipeline = DefaultEmbeddingPipeline(storage=storage)
        cache = MemoryEmbeddingCache()
        batch_processor = BatchProcessor(pipeline=pipeline, storage=storage)
        _embedding_service = EmbeddingService(
            storage=storage,
            pipeline=pipeline,
            cache=cache,
            batch_processor=batch_processor,
        )
    return _embedding_service


def set_embedding_service(service: EmbeddingService) -> None:
    global _embedding_service
    _embedding_service = service


def reset_embedding_service() -> None:
    global _embedding_service
    _embedding_service = None
