from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class EmbeddingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    DEPRECATED = "deprecated"


class EmbeddingProviderType(str, Enum):
    OLLAMA = "ollama"
    OPENAI = "openai"
    BGE = "bge"
    NOMIC = "nomic"
    E5 = "e5"
    INSTRUCTOR = "instructor"
    SENTENCE_TRANSFORMERS = "sentence_transformers"
    COHERE = "cohere"
    VOYAGEAI = "voyageai"
    AZURE_OPENAI = "azure_openai"
    MOCK = "mock"


class ChunkReference(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    content_hash: str
    chunk_index: int = 0


class EmbeddingRecord(BaseModel):
    id: str
    knowledge_id: str
    chunk_id: str
    chunk_index: int
    provider: EmbeddingProviderType
    model: str
    dimension: int
    version: int
    checksum: str
    content_hash: str
    status: EmbeddingStatus
    processing_time_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class EmbeddingVector(BaseModel):
    id: str
    knowledge_id: str
    chunk_id: str
    provider: EmbeddingProviderType
    model: str
    dimension: int
    version: int
    checksum: str
    content_hash: str
    status: EmbeddingStatus
    vector: list[float]
    processing_time_ms: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime


class EmbeddingVersion(BaseModel):
    version: int
    provider: EmbeddingProviderType
    model: str
    dimension: int
    checksum: str
    count: int
    knowledge_version: str = ""
    created_at: datetime
    is_active: bool = True


class EmbeddingBatch(BaseModel):
    id: str
    status: EmbeddingStatus
    total_chunks: int = 0
    processed_chunks: int = 0
    failed_chunks: int = 0
    provider: EmbeddingProviderType
    model: str
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None


class GenerateRequest(BaseModel):
    document_id: str | None = None
    chunk_ids: list[str] | None = None
    provider: EmbeddingProviderType | None = None
    model: str | None = None


class GenerateAllRequest(BaseModel):
    provider: EmbeddingProviderType | None = None
    model: str | None = None
    batch_size: int = 100


class GenerateResponse(BaseModel):
    embedding_id: str
    knowledge_id: str
    chunk_id: str
    provider: EmbeddingProviderType
    model: str
    dimension: int
    version: int
    status: EmbeddingStatus


class BatchGenerateResponse(BaseModel):
    batch_id: str
    status: EmbeddingStatus
    total_chunks: int
    processed_chunks: int
    failed_chunks: int


class EmbeddingListResponse(BaseModel):
    embeddings: list[EmbeddingRecord]
    total: int


class EmbeddingDetailResponse(BaseModel):
    id: str
    knowledge_id: str
    chunk_id: str
    chunk_index: int
    provider: EmbeddingProviderType
    model: str
    dimension: int
    version: int
    checksum: str
    content_hash: str
    status: EmbeddingStatus
    metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RebuildRequest(BaseModel):
    document_id: str | None = None
    chunk_ids: list[str] | None = None
    provider: EmbeddingProviderType | None = None
    model: str | None = None


class ProviderInfo(BaseModel):
    name: EmbeddingProviderType
    models: list[str] = []
    default_model: str = ""
    dimensions: int = 0


class PipelineConfig(BaseModel):
    batch_size: int = 50
    max_retries: int = 3
    retry_delay_ms: int = 100
    validate_vectors: bool = True
    skip_cache: bool = False


class BatchRequest(BaseModel):
    chunks: list[ChunkReference] = Field(min_length=1)
    provider: EmbeddingProviderType | None = None
    model: str | None = None
    batch_size: int = 50
    skip_cache: bool = False


class BatchResponse(BaseModel):
    batch_id: str
    status: EmbeddingStatus
    total_chunks: int
    processed_chunks: int
    failed_chunks: int
    errors: list[str] = []


class ReindexRequest(BaseModel):
    embedding_ids: list[str] = Field(min_length=1)
    provider: EmbeddingProviderType | None = None
    model: str | None = None
