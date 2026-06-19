from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class VectorProviderType(str, Enum):
    MEMORY = "memory"
    CHROMA = "chroma"


class SearchResult(BaseModel):
    embedding_id: str
    chunk_id: str | None = None
    knowledge_id: str | None = None
    score: float
    metadata: dict[str, Any] = Field(default_factory=dict)
    vector: list[float] | None = None


class SearchQuery(BaseModel):
    query_vector: list[float] | None = None
    query_text: str | None = None
    top_k: int = Field(default=10, ge=1, le=200)
    filters: dict[str, Any] | None = None
    include_vectors: bool = False


class SearchTextRequest(BaseModel):
    query_text: str = Field(min_length=1, max_length=10000)
    top_k: int = Field(default=10, ge=1, le=200)
    filters: dict[str, Any] | None = None
    include_vectors: bool = False


class SearchByVectorRequest(BaseModel):
    query_vector: list[float] = Field(min_length=1)
    top_k: int = Field(default=10, ge=1, le=200)
    filters: dict[str, Any] | None = None
    include_vectors: bool = False


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: int
    query_time_ms: float


class IndexRequest(BaseModel):
    knowledge_id: str | None = None
    chunk_ids: list[str] | None = None


class IndexResult(BaseModel):
    indexed_count: int
    skipped_count: int
    errors: list[str] = []


class IndexResponse(BaseModel):
    status: str
    result: IndexResult


class VectorStats(BaseModel):
    total_vectors: int
    provider: str
    dimension: int | None = None


class VectorDeleteResponse(BaseModel):
    deleted: bool
    embedding_id: str | None = None
    deleted_count: int | None = None


class ClearResponse(BaseModel):
    cleared: bool
    previous_count: int
