from app.ai.embeddings.exceptions.exceptions import (
    DimensionMismatchError,
    DuplicateEmbeddingError,
    EmptyChunkError,
    OversizedChunkError,
    ProviderError,
)
from app.ai.embeddings.interfaces.interfaces import EmbeddingStorage, EmbeddingValidator


class DefaultEmbeddingValidator(EmbeddingValidator):
    MAX_CHUNK_CHARS: int = 16384
    MIN_CHUNK_CHARS: int = 1

    async def validate_chunk(self, content: str, chunk_id: str) -> bool:
        if not content or not content.strip():
            raise EmptyChunkError(f"Chunk {chunk_id} has empty content")
        if len(content) < self.MIN_CHUNK_CHARS:
            raise EmptyChunkError(f"Chunk {chunk_id} content too short ({len(content)} chars)")
        if len(content) > self.MAX_CHUNK_CHARS:
            raise OversizedChunkError(
                f"Chunk {chunk_id} content exceeds {self.MAX_CHUNK_CHARS} chars ({len(content)})"
            )
        return True

    async def validate_vector(
        self, vector: list[float], expected_dimension: int, embedding_id: str
    ) -> bool:
        if len(vector) != expected_dimension:
            raise DimensionMismatchError(
                f"Embedding {embedding_id} dimension mismatch: "
                f"got {len(vector)}, expected {expected_dimension}"
            )
        if all(v == 0.0 for v in vector):
            raise DimensionMismatchError(f"Embedding {embedding_id} is all zeros")
        return True

    async def validate_checksum(self, content_hash: str, checksum: str) -> bool:
        return content_hash == checksum

    async def validate_provider_available(self, provider_type: str, model: str) -> bool:
        from app.ai.embeddings.schemas.schemas import EmbeddingProviderType
        try:
            EmbeddingProviderType(provider_type)
        except ValueError:
            raise ProviderError(f"Unknown provider type: {provider_type}")
        return True

    async def validate_no_duplicate(
        self, content_hash: str, provider: str, model: str, storage: EmbeddingStorage
    ) -> bool:
        records, _ = await storage.list_records(
            status="completed",
            offset=0,
            limit=10000,
        )
        for rec in records:
            if rec.content_hash == content_hash and rec.provider.value == provider and rec.model == model:
                raise DuplicateEmbeddingError(
                    f"Duplicate embedding for content hash {content_hash} "
                    f"with provider {provider} model {model}"
                )
        return True
