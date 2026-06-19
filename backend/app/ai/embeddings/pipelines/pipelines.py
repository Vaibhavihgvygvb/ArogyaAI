import time
from datetime import datetime, timezone

from app.ai.embeddings.cache.cache import MemoryEmbeddingCache
from app.ai.embeddings.exceptions.exceptions import PipelineError
from app.ai.embeddings.interfaces.interfaces import (
    EmbeddingCache,
    EmbeddingPipeline,
    EmbeddingProvider,
    EmbeddingStorage,
    EmbeddingValidator,
    EmbeddingVersionManager,
)
from app.ai.embeddings.schemas.schemas import (
    EmbeddingProviderType,
    EmbeddingRecord,
    EmbeddingStatus,
    EmbeddingVector,
    PipelineConfig,
)
from app.ai.embeddings.utils.utils import (
    compute_content_hash,
    compute_vector_checksum,
    generate_embedding_id,
    timing_ms,
)
from app.ai.embeddings.validators.validators import DefaultEmbeddingValidator
from app.ai.embeddings.versioning.versioning import InMemoryVersionManager


class DefaultEmbeddingPipeline(EmbeddingPipeline):
    def __init__(
        self,
        storage: EmbeddingStorage,
        validator: EmbeddingValidator | None = None,
        cache: EmbeddingCache | None = None,
        version_manager: EmbeddingVersionManager | None = None,
    ):
        self._storage = storage
        self._validator = validator or DefaultEmbeddingValidator()
        self._cache = cache or MemoryEmbeddingCache()
        self._version_manager = version_manager or InMemoryVersionManager()

    async def run(
        self,
        content: str,
        chunk_id: str,
        document_id: str,
        chunk_index: int,
        content_hash: str,
        provider: EmbeddingProvider,
        config: PipelineConfig | None = None,
    ) -> EmbeddingVector:
        cfg = config or PipelineConfig()

        await self._validator.validate_chunk(content, chunk_id)
        await self._validator.validate_provider_available(
            provider.provider_type().value, provider.default_model()
        )

        if not cfg.skip_cache:
            cached = await self._cache.get(
                content_hash, provider.provider_type().value, provider.default_model()
            )
            if cached is not None:
                return cached

        texts = [content]
        last_error: str | None = None
        embed_start = time.time()
        for attempt in range(cfg.max_retries):
            try:
                vectors = await provider.embed(texts)
                break
            except Exception as e:
                last_error = str(e)
                if attempt < cfg.max_retries - 1:
                    await self._sleep(cfg.retry_delay_ms)
                    continue
                raise PipelineError(f"Embedding failed after {cfg.max_retries} retries: {last_error}")
        else:
            raise PipelineError(f"Embedding failed after {cfg.max_retries} retries: {last_error}")

        processing_time_ms = round((time.time() - embed_start) * 1000, 2)
        vector_data = vectors[0]
        dimension = len(vector_data)

        if cfg.validate_vectors:
            await self._validator.validate_vector(
                vector_data, provider.dimensions(), generate_embedding_id()
            )

        checksum = compute_vector_checksum(vector_data)
        version = await self._version_manager.get_active_version(
            provider.provider_type().value, provider.default_model()
        ) or await self._version_manager.create_version(
            provider.provider_type().value,
            provider.default_model(),
            dimension,
            checksum,
            1,
        )

        now = datetime.now(timezone.utc)
        embedding_id = generate_embedding_id()

        vector = EmbeddingVector(
            id=embedding_id,
            knowledge_id=document_id,
            chunk_id=chunk_id,
            provider=provider.provider_type(),
            model=provider.default_model(),
            dimension=dimension,
            version=version,
            checksum=checksum,
            content_hash=content_hash,
            status=EmbeddingStatus.COMPLETED,
            vector=vector_data,
            processing_time_ms=processing_time_ms,
            metadata={
                "chunk_index": chunk_index,
                "content_length": len(content),
            },
            created_at=now,
            updated_at=now,
        )

        record = EmbeddingRecord(
            id=embedding_id,
            knowledge_id=document_id,
            chunk_id=chunk_id,
            chunk_index=chunk_index,
            provider=provider.provider_type(),
            model=provider.default_model(),
            dimension=dimension,
            version=version,
            checksum=checksum,
            content_hash=content_hash,
            status=EmbeddingStatus.COMPLETED,
            processing_time_ms=processing_time_ms,
            metadata={
                "chunk_index": chunk_index,
                "content_length": len(content),
            },
            created_at=now,
            updated_at=now,
        )

        if not cfg.skip_cache:
            await self._cache.set(vector)

        await self._storage.store_vector(vector)
        await self._storage.store_record(record)

        return vector

    async def _sleep(self, ms: int) -> None:
        import asyncio
        await asyncio.sleep(ms / 1000)
