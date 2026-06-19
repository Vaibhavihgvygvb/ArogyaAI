import asyncio
from datetime import datetime, timezone

from app.ai.embeddings.exceptions.exceptions import BatchError
from app.ai.embeddings.interfaces.interfaces import EmbeddingPipeline, EmbeddingProvider, EmbeddingStorage
from app.ai.embeddings.schemas.schemas import (
    ChunkReference,
    EmbeddingBatch,
    EmbeddingStatus,
    PipelineConfig,
)
from app.ai.embeddings.utils.utils import compute_content_hash, generate_batch_id


class BatchProcessor:
    def __init__(
        self,
        pipeline: EmbeddingPipeline,
        storage: EmbeddingStorage,
    ):
        self._pipeline = pipeline
        self._storage = storage

    async def process_chunks(
        self,
        chunks: list[ChunkReference],
        provider: EmbeddingProvider,
        config: PipelineConfig | None = None,
    ) -> EmbeddingBatch:
        cfg = config or PipelineConfig()
        batch_id = generate_batch_id()
        now = datetime.now(timezone.utc)

        batch = EmbeddingBatch(
            id=batch_id,
            status=EmbeddingStatus.PROCESSING,
            total_chunks=len(chunks),
            processed_chunks=0,
            failed_chunks=0,
            provider=provider.provider_type(),
            model=provider.default_model(),
            created_at=now,
        )

        for i in range(0, len(chunks), cfg.batch_size):
            chunk_batch = chunks[i : i + cfg.batch_size]
            tasks = []
            for chunk in chunk_batch:
                tasks.append(self._process_single(chunk, provider, cfg))

            results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in results:
                if isinstance(result, Exception):
                    batch.failed_chunks += 1
                else:
                    batch.processed_chunks += 1

        batch.status = (
            EmbeddingStatus.COMPLETED
            if batch.failed_chunks == 0
            else EmbeddingStatus.FAILED
        )
        batch.completed_at = datetime.now(timezone.utc)

        if batch.failed_chunks > 0 and batch.processed_chunks > 0:
            batch.status = EmbeddingStatus.COMPLETED

        return batch

    async def _process_single(
        self,
        chunk: ChunkReference,
        provider: EmbeddingProvider,
        config: PipelineConfig,
    ) -> None:
        content_hash = chunk.content_hash or compute_content_hash(chunk.content)
        await self._pipeline.run(
            content=chunk.content,
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            content_hash=content_hash,
            provider=provider,
            config=config,
        )
