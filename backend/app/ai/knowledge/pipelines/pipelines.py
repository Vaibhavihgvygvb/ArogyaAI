import time
from datetime import datetime, timezone
from typing import IO

from app.ai.knowledge.catalog.catalog import KnowledgeCatalog
from app.ai.knowledge.chunkers.chunkers import ChunkerFactory
from app.ai.knowledge.cleaners.cleaners import CompositeCleaner
from app.ai.knowledge.exceptions.exceptions import PipelineError
from app.ai.knowledge.interfaces.interfaces import Loader, Parser, StorageProvider, Validator
from app.ai.knowledge.loaders.loaders import LoaderFactory
from app.ai.knowledge.metadata.metadata import DefaultMetadataExtractor
from app.ai.knowledge.normalizers.normalizers import CompositeNormalizer
from app.ai.knowledge.parsers.parsers import DocumentParser
from app.ai.knowledge.schemas.schemas import (
    CatalogEntry,
    ChunkingStrategy,
    DocumentChunk,
    DocumentFormat,
    DocumentMetadata,
    DocumentStatus,
    KnowledgeDocument,
    PipelineResult,
    PipelineStageResult,
    ProcessingConfig,
)
from app.ai.knowledge.utils.utils import compute_checksum, generate_document_id, timing_ms
from app.ai.knowledge.validators.validators import DocumentValidator


def _get_format_from_filename(filename: str) -> DocumentFormat:
    ext = filename.rsplit(".", 1)[-1].lower()
    for fmt in DocumentFormat:
        if fmt.value == ext:
            return fmt
    raise PipelineError(f"Unsupported file extension: .{ext}")


class ProcessingPipeline:
    def __init__(
        self,
        storage: StorageProvider,
        catalog: KnowledgeCatalog,
        loader_factory: LoaderFactory | None = None,
        parser: Parser | None = None,
        normalizer: CompositeNormalizer | None = None,
        cleaner: CompositeCleaner | None = None,
        metadata_extractor: DefaultMetadataExtractor | None = None,
        chunker_factory: ChunkerFactory | None = None,
        validator: Validator | None = None,
    ):
        self._storage = storage
        self._catalog = catalog
        self._loader_factory = loader_factory or LoaderFactory()
        self._parser = parser or DocumentParser()
        self._normalizer = normalizer or CompositeNormalizer()
        self._cleaner = cleaner or CompositeCleaner()
        self._metadata_extractor = metadata_extractor or DefaultMetadataExtractor()
        self._chunker_factory = chunker_factory or ChunkerFactory()
        self._validator = validator or DocumentValidator()

    async def run(
        self,
        file: IO,
        filename: str,
        raw_bytes: bytes,
        config: ProcessingConfig | None = None,
    ) -> PipelineResult:
        cfg = config or ProcessingConfig()
        start_time = time.time()
        stages: list[PipelineStageResult] = []
        document_id = generate_document_id()
        fmt = _get_format_from_filename(filename)
        checksum = compute_checksum(raw_bytes)

        if fmt not in cfg.allowed_formats:
            return PipelineResult(
                document_id=document_id,
                success=False,
                stages=stages,
                total_duration_ms=timing_ms(start_time),
                error=f"Format {fmt} not in allowed formats",
            )

        try:
            import_stage = await self._run_import(file, filename, fmt, raw_bytes, checksum, cfg, stages)
            if not import_stage.success:
                return PipelineResult(
                    document_id=document_id,
                    success=False,
                    stages=stages,
                    total_duration_ms=timing_ms(start_time),
                    error=import_stage.error,
                )

            content = import_stage.details.get("content", "")

            parse_stage = await self._run_parse(content, fmt, stages)
            if not parse_stage.success:
                return self._fail(document_id, stages, start_time, parse_stage.error)
            content = parse_stage.details.get("content", "")

            normalize_stage = await self._run_normalize(content, cfg, stages)
            if not normalize_stage.success:
                return self._fail(document_id, stages, start_time, normalize_stage.error)
            content = normalize_stage.details.get("content", "")

            clean_stage = await self._run_clean(content, cfg, stages)
            if not clean_stage.success:
                return self._fail(document_id, stages, start_time, clean_stage.error)
            content = clean_stage.details.get("content", "")

            metadata_stage = await self._run_metadata_extraction(content, filename, stages)
            metadata = metadata_stage.details.get("metadata", DocumentMetadata())

            validate_stage = await self._run_validation(content, cfg, stages)
            if not validate_stage.success:
                return self._fail(document_id, stages, start_time, validate_stage.error)

            chunk_stage = await self._run_chunking(content, cfg, stages)
            chunks = chunk_stage.details.get("chunks", [])

            version = 1
            doc = KnowledgeDocument(
                id=document_id,
                filename=filename,
                format=fmt,
                size_bytes=len(raw_bytes),
                checksum=checksum,
                status=DocumentStatus.COMPLETED,
                version=version,
                metadata=metadata,
                chunks=chunks,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )

            store_stage = await self._run_store(doc, stages)
            if not store_stage.success:
                return self._fail(document_id, stages, start_time, store_stage.error)

            total_time = timing_ms(start_time)
            return PipelineResult(
                document_id=document_id,
                success=True,
                stages=stages,
                total_duration_ms=total_time,
            )

        except Exception as e:
            return self._fail(document_id, stages, start_time, str(e))

    async def _run_import(
        self,
        file: IO,
        filename: str,
        fmt: DocumentFormat,
        raw_bytes: bytes,
        checksum: str,
        cfg: ProcessingConfig,
        stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        stage_start = time.time()
        try:
            await self._validator.validate_format(filename, fmt)
            await self._validator.validate_size(len(raw_bytes), cfg.max_file_size_mb)
            await self._validator.validate_encoding(raw_bytes)
            loader = self._loader_factory.get_loader(fmt)
            content = await loader.load(file, fmt)
            quality_ok, quality_err = await self._validator.validate_content_quality(content)
            if not quality_ok:
                raise PipelineError(quality_err or "Content quality check failed")
            result = PipelineStageResult(
                stage="import",
                success=True,
                duration_ms=timing_ms(stage_start),
                details={"content": content},
            )
            stages.append(result)
            return result
        except Exception as e:
            result = PipelineStageResult(
                stage="import", success=False, duration_ms=timing_ms(stage_start), error=str(e)
            )
            stages.append(result)
            return result

    async def _run_parse(
        self,
        content: str,
        fmt: DocumentFormat,
        stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        stage_start = time.time()
        try:
            parsed = await self._parser.parse(content, fmt)
            result = PipelineStageResult(
                stage="parse",
                success=True,
                duration_ms=timing_ms(stage_start),
                details={"content": parsed},
            )
            stages.append(result)
            return result
        except Exception as e:
            result = PipelineStageResult(
                stage="parse", success=False, duration_ms=timing_ms(stage_start), error=str(e)
            )
            stages.append(result)
            return result

    async def _run_normalize(
        self,
        content: str,
        cfg: ProcessingConfig,
        stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        stage_start = time.time()
        if cfg.skip_normalization:
            result = PipelineStageResult(
                stage="normalize", success=True, duration_ms=timing_ms(stage_start),
                details={"content": content, "skipped": True},
            )
            stages.append(result)
            return result
        try:
            normalized = await self._normalizer.normalize(content)
            result = PipelineStageResult(
                stage="normalize",
                success=True,
                duration_ms=timing_ms(stage_start),
                details={"content": normalized},
            )
            stages.append(result)
            return result
        except Exception as e:
            result = PipelineStageResult(
                stage="normalize", success=False, duration_ms=timing_ms(stage_start), error=str(e)
            )
            stages.append(result)
            return result

    async def _run_clean(
        self,
        content: str,
        cfg: ProcessingConfig,
        stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        stage_start = time.time()
        if cfg.skip_cleaning:
            result = PipelineStageResult(
                stage="clean", success=True, duration_ms=timing_ms(stage_start),
                details={"content": content, "skipped": True},
            )
            stages.append(result)
            return result
        try:
            cleaned = await self._cleaner.clean(content)
            result = PipelineStageResult(
                stage="clean",
                success=True,
                duration_ms=timing_ms(stage_start),
                details={"content": cleaned},
            )
            stages.append(result)
            return result
        except Exception as e:
            result = PipelineStageResult(
                stage="clean", success=False, duration_ms=timing_ms(stage_start), error=str(e)
            )
            stages.append(result)
            return result

    async def _run_metadata_extraction(
        self,
        content: str,
        filename: str,
        stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        stage_start = time.time()
        try:
            metadata = await self._metadata_extractor.extract(content, filename)
            result = PipelineStageResult(
                stage="metadata",
                success=True,
                duration_ms=timing_ms(stage_start),
                details={"metadata": metadata},
            )
            stages.append(result)
            return result
        except Exception as e:
            result = PipelineStageResult(
                stage="metadata", success=False, duration_ms=timing_ms(stage_start), error=str(e)
            )
            stages.append(result)
            return result

    async def _run_validation(
        self,
        content: str,
        cfg: ProcessingConfig,
        stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        stage_start = time.time()
        if cfg.skip_validation:
            result = PipelineStageResult(
                stage="validate", success=True, duration_ms=timing_ms(stage_start),
                details={"skipped": True},
            )
            stages.append(result)
            return result
        try:
            quality_ok, quality_err = await self._validator.validate_content_quality(content)
            if not quality_ok:
                raise PipelineError(quality_err or "Content quality validation failed")
            result = PipelineStageResult(
                stage="validate",
                success=True,
                duration_ms=timing_ms(stage_start),
                details={"quality_ok": quality_ok},
            )
            stages.append(result)
            return result
        except Exception as e:
            result = PipelineStageResult(
                stage="validate", success=False, duration_ms=timing_ms(stage_start), error=str(e)
            )
            stages.append(result)
            return result

    async def _run_chunking(
        self,
        content: str,
        cfg: ProcessingConfig,
        stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        stage_start = time.time()
        if cfg.skip_chunking:
            result = PipelineStageResult(
                stage="chunk", success=True, duration_ms=timing_ms(stage_start),
                details={"chunks": [], "skipped": True},
            )
            stages.append(result)
            return result
        try:
            headings = await self._parser.extract_headings(content)
            chunker = self._chunker_factory.get_chunker(cfg.chunking_strategy.value)
            chunks = await chunker.chunk(content, cfg, headings)
            result = PipelineStageResult(
                stage="chunk",
                success=True,
                duration_ms=timing_ms(stage_start),
                details={"chunks": chunks, "chunk_count": len(chunks)},
            )
            stages.append(result)
            return result
        except Exception as e:
            result = PipelineStageResult(
                stage="chunk", success=False, duration_ms=timing_ms(stage_start), error=str(e)
            )
            stages.append(result)
            return result

    async def _run_store(
        self,
        doc: KnowledgeDocument,
        stages: list[PipelineStageResult],
    ) -> PipelineStageResult:
        stage_start = time.time()
        try:
            await self._storage.store(doc)
            catalog_entry = CatalogEntry(
                id=doc.id,
                filename=doc.filename,
                format=doc.format,
                size_bytes=doc.size_bytes,
                status=DocumentStatus.COMPLETED,
                version=doc.version,
                metadata=doc.metadata,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            self._catalog.add_entry(catalog_entry)
            result = PipelineStageResult(
                stage="store",
                success=True,
                duration_ms=timing_ms(stage_start),
                details={"document_id": doc.id},
            )
            stages.append(result)
            return result
        except Exception as e:
            result = PipelineStageResult(
                stage="store", success=False, duration_ms=timing_ms(stage_start), error=str(e)
            )
            stages.append(result)
            return result

    def _fail(
        self,
        document_id: str,
        stages: list[PipelineStageResult],
        start_time: float,
        error: str | None,
    ) -> PipelineResult:
        return PipelineResult(
            document_id=document_id,
            success=False,
            stages=stages,
            total_duration_ms=timing_ms(start_time),
            error=error,
        )
