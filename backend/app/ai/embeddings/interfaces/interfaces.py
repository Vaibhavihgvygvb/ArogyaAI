from abc import ABC, abstractmethod

from app.ai.embeddings.schemas.schemas import (
    EmbeddingProviderType,
    EmbeddingRecord,
    EmbeddingVector,
    PipelineConfig,
)


class EmbeddingProvider(ABC):
    @abstractmethod
    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        pass

    @abstractmethod
    def provider_type(self) -> EmbeddingProviderType:
        pass

    @abstractmethod
    def default_model(self) -> str:
        pass

    @abstractmethod
    def dimensions(self) -> int:
        pass

    @abstractmethod
    def supported_models(self) -> list[str]:
        pass


class EmbeddingValidator(ABC):
    @abstractmethod
    async def validate_chunk(self, content: str, chunk_id: str) -> bool:
        pass

    @abstractmethod
    async def validate_vector(
        self, vector: list[float], expected_dimension: int, embedding_id: str
    ) -> bool:
        pass

    @abstractmethod
    async def validate_checksum(self, content_hash: str, checksum: str) -> bool:
        pass

    @abstractmethod
    async def validate_provider_available(self, provider_type: str, model: str) -> bool:
        pass

    @abstractmethod
    async def validate_no_duplicate(
        self, content_hash: str, provider: str, model: str, storage: "EmbeddingStorage"
    ) -> bool:
        pass


class EmbeddingCache(ABC):
    @abstractmethod
    async def get(self, content_hash: str, provider: str, model: str) -> EmbeddingVector | None:
        pass

    @abstractmethod
    async def set(self, vector: EmbeddingVector) -> None:
        pass

    @abstractmethod
    async def has(self, content_hash: str, provider: str, model: str) -> bool:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @abstractmethod
    async def invalidate(self, content_hash: str) -> None:
        pass


class EmbeddingVersionManager(ABC):
    @abstractmethod
    async def create_version(
        self, provider: str, model: str, dimension: int, checksum: str, count: int
    ) -> int:
        pass

    @abstractmethod
    async def get_active_version(self, provider: str, model: str) -> int | None:
        pass

    @abstractmethod
    async def deprecate_version(self, provider: str, model: str, version: int) -> None:
        pass

    @abstractmethod
    async def get_versions(self, provider: str, model: str) -> list[int]:
        pass

    @abstractmethod
    async def rollback(self, provider: str, model: str, target_version: int) -> int | None:
        pass

    @abstractmethod
    async def get_version_info(self, provider: str, model: str, version: int):
        pass


class EmbeddingStorage(ABC):
    @abstractmethod
    async def store_vector(self, vector: EmbeddingVector) -> str:
        pass

    @abstractmethod
    async def store_record(self, record: EmbeddingRecord) -> str:
        pass

    @abstractmethod
    async def get_vector(self, embedding_id: str) -> EmbeddingVector | None:
        pass

    @abstractmethod
    async def get_record(self, embedding_id: str) -> EmbeddingRecord | None:
        pass

    @abstractmethod
    async def delete(self, embedding_id: str) -> bool:
        pass

    @abstractmethod
    async def list_records(
        self,
        knowledge_id: str | None = None,
        chunk_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[EmbeddingRecord], int]:
        pass

    @abstractmethod
    async def exists(self, embedding_id: str) -> bool:
        pass


class EmbeddingPipeline(ABC):
    @abstractmethod
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
        pass
