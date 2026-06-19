from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class DocumentFormat(str, Enum):
    TXT = "txt"
    MD = "md"
    PDF = "pdf"
    DOCX = "docx"
    HTML = "html"
    CSV = "csv"
    JSON = "json"


class ChunkingStrategy(str, Enum):
    FIXED = "fixed"
    PARAGRAPH = "paragraph"
    HEADING_AWARE = "heading_aware"
    SLIDING_WINDOW = "sliding_window"


class DocumentStatus(str, Enum):
    PENDING = "pending"
    IMPORTING = "importing"
    PARSING = "parsing"
    NORMALIZING = "normalizing"
    CLEANING = "cleaning"
    VALIDATING = "validating"
    CHUNKING = "chunking"
    COMPLETED = "completed"
    FAILED = "failed"


class ChunkMetadata(BaseModel):
    source_document: str
    chunk_index: int
    heading_path: list[str] = []
    char_start: int = 0
    char_end: int = 0
    word_count: int = 0


class DocumentChunk(BaseModel):
    id: str
    content: str
    metadata: ChunkMetadata


class DocumentMetadata(BaseModel):
    title: str = ""
    author: str = ""
    specialty: str = ""
    tags: list[str] = []
    language: str = ""
    word_count: int = 0
    char_count: int = 0
    page_count: int | None = None


class KnowledgeDocument(BaseModel):
    id: str
    filename: str
    format: DocumentFormat
    size_bytes: int
    checksum: str
    status: DocumentStatus
    version: int = 1
    metadata: DocumentMetadata = Field(default_factory=DocumentMetadata)
    chunks: list[DocumentChunk] = []
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class ImportResult(BaseModel):
    document_id: str
    filename: str
    format: DocumentFormat
    status: DocumentStatus
    chunk_count: int = 0
    error: str | None = None


class CatalogEntry(BaseModel):
    id: str
    filename: str
    format: DocumentFormat
    size_bytes: int
    status: DocumentStatus
    version: int
    metadata: DocumentMetadata
    created_at: datetime
    updated_at: datetime


class DocumentVersion(BaseModel):
    version: int
    checksum: str
    size_bytes: int
    created_at: datetime


class ProcessingConfig(BaseModel):
    chunk_size: int = 500
    chunk_overlap: int = 50
    chunking_strategy: ChunkingStrategy = ChunkingStrategy.PARAGRAPH
    skip_parsing: bool = False
    skip_normalization: bool = False
    skip_cleaning: bool = False
    skip_validation: bool = False
    skip_chunking: bool = False
    max_file_size_mb: int = 10
    allowed_formats: list[DocumentFormat] = Field(default_factory=lambda: list(DocumentFormat))


class ImportRequest(BaseModel):
    chunk_size: int | None = None
    chunk_overlap: int | None = None
    chunking_strategy: ChunkingStrategy | None = None


class ImportResponse(BaseModel):
    document_id: str
    filename: str
    format: DocumentFormat
    status: DocumentStatus
    chunk_count: int
    message: str


class DocumentResponse(BaseModel):
    id: str
    filename: str
    format: DocumentFormat
    size_bytes: int
    checksum: str
    status: DocumentStatus
    version: int
    metadata: DocumentMetadata
    chunks: list[DocumentChunk]
    error: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    documents: list[CatalogEntry]
    total: int


class DocumentVersionsResponse(BaseModel):
    document_id: str
    filename: str
    versions: list[DocumentVersion]


class DeleteResponse(BaseModel):
    deleted: bool
    document_id: str


class PipelineStageResult(BaseModel):
    stage: str
    success: bool
    duration_ms: float
    error: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class PipelineResult(BaseModel):
    document_id: str
    success: bool
    stages: list[PipelineStageResult]
    total_duration_ms: float
    error: str | None = None
