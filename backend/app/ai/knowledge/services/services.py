import io
import os
from datetime import datetime
from typing import IO

from app.ai.knowledge.catalog.catalog import KnowledgeCatalog
from app.ai.knowledge.chunkers.chunkers import ChunkerFactory
from app.ai.knowledge.cleaners.cleaners import CompositeCleaner
from app.ai.knowledge.exceptions.exceptions import DocumentNotFoundError
from app.ai.knowledge.interfaces.interfaces import StorageProvider
from app.ai.knowledge.loaders.loaders import LoaderFactory
from app.ai.knowledge.metadata.metadata import DefaultMetadataExtractor
from app.ai.knowledge.normalizers.normalizers import CompositeNormalizer
from app.ai.knowledge.parsers.parsers import DocumentParser
from app.ai.knowledge.pipelines.pipelines import ProcessingPipeline
from app.ai.knowledge.schemas.schemas import (
    CatalogEntry,
    ChunkingStrategy,
    DocumentChunk,
    DocumentFormat,
    DocumentStatus,
    DocumentVersion,
    ImportRequest,
    ImportResult,
    KnowledgeDocument,
    ProcessingConfig,
)
from app.ai.knowledge.utils.utils import generate_document_id, compute_checksum
from app.ai.knowledge.validators.validators import DocumentValidator


class KnowledgeService:
    def __init__(
        self,
        storage: StorageProvider,
        catalog: KnowledgeCatalog,
        pipeline: ProcessingPipeline | None = None,
    ):
        self._storage = storage
        self._catalog = catalog
        self._pipeline = pipeline or ProcessingPipeline(
            storage=storage,
            catalog=catalog,
        )

    async def import_document(
        self,
        file: IO,
        filename: str,
        config: ImportRequest | None = None,
    ) -> ImportResult:
        raw_bytes = file.read()
        if not isinstance(raw_bytes, bytes):
            raw_bytes = raw_bytes.encode("utf-8") if isinstance(raw_bytes, str) else raw_bytes

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        try:
            fmt = DocumentFormat(ext)
        except ValueError:
            return ImportResult(
                document_id="",
                filename=filename,
                format=DocumentFormat.TXT,
                status=DocumentStatus.FAILED,
                error=f"Unsupported file extension: .{ext}",
            )

        cfg = ProcessingConfig()
        if config:
            if config.chunk_size is not None:
                cfg.chunk_size = config.chunk_size
            if config.chunk_overlap is not None:
                cfg.chunk_overlap = config.chunk_overlap
            if config.chunking_strategy is not None:
                cfg.chunking_strategy = config.chunking_strategy

        file_obj = io.BytesIO(raw_bytes)
        result = await self._pipeline.run(file_obj, filename, raw_bytes, cfg)

        if not result.success:
            import_stage = next((s for s in result.stages if s.stage == "import"), None)
            doc_id = import_stage.details.get("document_id", "") if import_stage else ""
            self._catalog.update_entry(
                document_id=doc_id or result.document_id,
                status=DocumentStatus.FAILED,
            )
            return ImportResult(
                document_id=result.document_id,
                filename=filename,
                format=fmt,
                status=DocumentStatus.FAILED,
                error=result.error,
            )

        return ImportResult(
            document_id=result.document_id,
            filename=filename,
            format=fmt,
            status=DocumentStatus.COMPLETED,
            chunk_count=len(await self._get_chunks_count(result.document_id)),
        )

    async def _get_chunks_count(self, document_id: str) -> list:
        doc = await self._storage.retrieve(document_id)
        return doc.chunks if doc else []

    async def get_document(self, document_id: str) -> KnowledgeDocument | None:
        return await self._storage.retrieve(document_id)

    async def list_documents(
        self,
        status: DocumentStatus | None = None,
        format: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[CatalogEntry], int]:
        all_entries = self._catalog.list_entries(
            status=status, format=format, offset=0, limit=10000
        )
        total = len(all_entries)
        entries = all_entries[offset : offset + limit]
        return entries, total

    async def delete_document(self, document_id: str) -> bool:
        exists = await self._storage.document_exists(document_id)
        if not exists:
            return False
        await self._storage.delete(document_id)
        self._catalog.remove_entry(document_id)
        return True

    async def get_document_versions(self, document_id: str) -> list[DocumentVersion]:
        doc = await self._storage.retrieve(document_id)
        if doc is None:
            raise DocumentNotFoundError(f"Document not found: {document_id}")
        return [
            DocumentVersion(
                version=doc.version,
                checksum=doc.checksum,
                size_bytes=doc.size_bytes,
                created_at=doc.created_at,
            )
        ]

    async def get_chunk(self, document_id: str, chunk_id: str) -> DocumentChunk | None:
        doc = await self._storage.retrieve(document_id)
        if doc is None:
            return None
        for chunk in doc.chunks:
            if chunk.id == chunk_id:
                return chunk
        return None

    async def document_exists(self, document_id: str) -> bool:
        return await self._storage.document_exists(document_id)
