from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RetrievalResult(BaseModel):
    chunk_id: str
    knowledge_id: str
    document_id: str | None = None
    content: str | None = None
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    rank: int = 0


class RetrievalQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000, description="Natural language query")
    top_k: int = Field(10, ge=1, le=200, description="Maximum number of results to return")
    filters: dict[str, Any] | None = Field(None, description="Metadata filters for vector search")
    min_score: float | None = Field(None, ge=0.0, le=1.0, description="Minimum similarity score threshold")
    include_vectors: bool = False
    include_chunks: bool = True
    rerank: bool = True


class RetrievalResponse(BaseModel):
    results: list[RetrievalResult]
    total: int
    query: str
    query_time_ms: float = 0.0


class ContextAssembly(BaseModel):
    context: str
    token_count: int = 0
    chunk_count: int = 0
    truncated: bool = False


class RAGRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000, description="Natural language query")
    conversation_id: str | None = Field(None, description="Existing conversation ID for memory")
    prompt_name: str | None = Field(None, description="Prompt template name to use")
    prompt_variables: dict[str, Any] | None = Field(None, description="Additional prompt variables")
    top_k: int = Field(5, ge=1, le=50, description="Number of chunks to retrieve")
    filters: dict[str, Any] | None = Field(None, description="Metadata filters for retrieval")
    min_score: float | None = Field(None, ge=0.0, le=1.0, description="Minimum similarity score")
    system_message: str | None = Field(None, description="Override default RAG system message")
    temperature: float | None = Field(None, ge=0.0, le=2.0, description="Generation temperature")
    max_tokens: int | None = Field(None, ge=1, le=16384, description="Maximum tokens to generate")
    stream: bool = False
    max_context_tokens: int = Field(2048, ge=128, le=16384, description="Max tokens for context assembly")


class RAGResponse(BaseModel):
    answer: str
    conversation_id: str | None = None
    sources: list[RetrievalResult] = Field(default_factory=list)
    model: str = ""
    provider: str = ""
    usage: dict[str, Any] | None = None
    retrieval_time_ms: float = 0.0
    generation_time_ms: float = 0.0


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=10000)
    top_k: int = Field(10, ge=1, le=200)
    filters: dict[str, Any] | None = None
    min_score: float | None = Field(None, ge=0.0, le=1.0)
    include_chunks: bool = True
    rerank: bool = True


class SearchResponse(BaseModel):
    results: list[RetrievalResult]
    total: int
    query: str
    query_time_ms: float = 0.0
