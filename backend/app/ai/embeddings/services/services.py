from typing import Any

from app.ai.embeddings.batch.batch import BatchProcessor
from app.ai.embeddings.cache.cache import MemoryEmbeddingCache
from app.ai.embeddings.exceptions.exceptions import DocumentNotFoundError, EmbeddingError
from app.ai.embeddings.interfaces.interfaces import (
    EmbeddingCache,
    EmbeddingPipeline,
    EmbeddingProvider,
    EmbeddingStorage,
)
from app.ai.embeddings.pipelines.pipelines import DefaultEmbeddingPipeline
from app.ai.embeddings.schemas.schemas import (
    ChunkReference,
    EmbeddingBatch,
    EmbeddingProviderType,
    EmbeddingRecord,
    EmbeddingStatus,
    EmbeddingVector,
    PipelineConfig,
)
from app.ai.embeddings.storage.storage import LocalEmbeddingStorage
from app.ai.embeddings.utils.utils import compute_content_hash
from app.ai.embeddings.validators.validators import DefaultEmbeddingValidator
from app.ai.embeddings.versioning.versioning import InMemoryVersionManager


class EmbeddingService:
    def __init__(
        self,
        storage: EmbeddingStorage,
        pipeline: EmbeddingPipeline | None = None,
        cache: EmbeddingCache | None = None,
        batch_processor: BatchProcessor | None = None,
    ):
        self._storage = storage
        self._pipeline = pipeline or DefaultEmbeddingPipeline(storage=storage)
        self._cache = cache or MemoryEmbeddingCache()
        self._batch_processor = batch_processor or BatchProcessor(pipeline=self._pipeline, storage=storage)

    async def generate(
        self,
        content: str,
        chunk_id: str,
        document_id: str,
        chunk_index: int = 0,
        provider: EmbeddingProvider | None = None,
        config: PipelineConfig | None = None,
        skip_duplicate_check: bool = False,
    ) -> EmbeddingVector:
        from app.ai.embeddings.providers.mock import MockEmbeddingProvider
        p = provider or MockEmbeddingProvider()
        content_hash = compute_content_hash(content)
        cfg = config or PipelineConfig()

        if not skip_duplicate_check and not cfg.skip_cache:
            try:
                await self._pipeline._validator.validate_no_duplicate(
                    content_hash, p.provider_type().value, p.default_model(), self._storage
                )
            except Exception:
                existing = await self._cache.get(
                    content_hash, p.provider_type().value, p.default_model()
                )
                if existing is not None:
                    return existing

        return await self._pipeline.run(
            content=content,
            chunk_id=chunk_id,
            document_id=document_id,
            chunk_index=chunk_index,
            content_hash=content_hash,
            provider=p,
            config=config,
        )

    async def generate_batch(
        self,
        chunks: list[ChunkReference],
        provider: EmbeddingProvider | None = None,
        config: PipelineConfig | None = None,
    ) -> EmbeddingBatch:
        from app.ai.embeddings.providers.mock import MockEmbeddingProvider
        p = provider or MockEmbeddingProvider()
        return await self._batch_processor.process_chunks(chunks, p, config)

    async def get_embedding(self, embedding_id: str) -> EmbeddingVector | None:
        return await self._storage.get_vector(embedding_id)

    async def get_record(self, embedding_id: str) -> EmbeddingRecord | None:
        return await self._storage.get_record(embedding_id)

    async def list_embeddings(
        self,
        knowledge_id: str | None = None,
        chunk_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[EmbeddingRecord], int]:
        return await self._storage.list_records(
            knowledge_id=knowledge_id,
            chunk_id=chunk_id,
            status=status,
            offset=offset,
            limit=limit,
        )

    async def delete_embedding(self, embedding_id: str) -> bool:
        return await self._storage.delete(embedding_id)

    async def rebuild(
        self,
        chunks: list[ChunkReference],
        provider: EmbeddingProvider | None = None,
        config: PipelineConfig | None = None,
    ) -> EmbeddingBatch:
        from app.ai.embeddings.providers.mock import MockEmbeddingProvider
        p = provider or MockEmbeddingProvider()
        cfg = config or PipelineConfig()
        cfg.skip_cache = True
        return await self._batch_processor.process_chunks(chunks, p, cfg)

    async def get_providers(self) -> list[dict[str, Any]]:
        return [
            {
                "name": EmbeddingProviderType.MOCK.value,
                "models": ["mock-embedding-v1", "mock-large-v2"],
                "default_model": "mock-embedding-v1",
                "dimensions": 384,
            },
        ]
