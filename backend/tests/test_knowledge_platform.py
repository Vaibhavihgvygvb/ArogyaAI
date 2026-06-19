import io
import json
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.knowledge.catalog.catalog import KnowledgeCatalog
from app.ai.knowledge.chunkers.chunkers import (
    ChunkerFactory,
    FixedSizeChunker,
    HeadingAwareChunker,
    ParagraphChunker,
    SlidingWindowChunker,
)
from app.ai.knowledge.cleaners.cleaners import BoilerplateRemover, CompositeCleaner, HeaderFooterStripper
from app.ai.knowledge.exceptions.exceptions import (
    DocumentNotFoundError,
    EncodingError,
    FileSizeExceededError,
    InvalidDocumentError,
    KnowledgeError,
    UnsupportedFormatError,
)
from app.ai.knowledge.interfaces.interfaces import Chunker, Cleaner, Loader, Normalizer, Parser, StorageProvider, Validator
from app.ai.knowledge.loaders.loaders import (
    CSVLoader,
    DOCXLoader,
    HTMLLoader,
    JSONLoader,
    LoaderFactory,
    PDFLoader,
    TextLoader,
)
from app.ai.knowledge.metadata.metadata import DefaultMetadataExtractor
from app.ai.knowledge.normalizers.normalizers import (
    CompositeNormalizer,
    NumberingNormalizer,
    QuoteNormalizer,
    UnicodeNormalizer,
    WhitespaceNormalizer,
)
from app.ai.knowledge.parsers.parsers import DocumentParser
from app.ai.knowledge.pipelines.pipelines import ProcessingPipeline
from app.ai.knowledge.schemas.schemas import (
    CatalogEntry,
    ChunkingStrategy,
    DocumentChunk,
    DocumentFormat,
    DocumentMetadata,
    DocumentStatus,
    ImportRequest,
    ImportResponse,
    KnowledgeDocument,
    ProcessingConfig,
)
from app.ai.knowledge.services.deps import get_knowledge_service, reset_knowledge_service, set_knowledge_service
from app.ai.knowledge.services.services import KnowledgeService
from app.ai.knowledge.storage.storage import LocalFileStorage
from app.ai.knowledge.utils.utils import compute_checksum, generate_document_id
from app.ai.knowledge.validators.validators import DocumentValidator


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class TestKnowledgeExceptions:
    def test_knowledge_error_base(self):
        assert issubclass(DocumentNotFoundError, KnowledgeError)
        assert issubclass(UnsupportedFormatError, InvalidDocumentError)
        assert issubclass(FileSizeExceededError, InvalidDocumentError)
        assert issubclass(EncodingError, InvalidDocumentError)

    def test_exception_raise_and_message(self):
        with pytest.raises(DocumentNotFoundError, match="not found"):
            raise DocumentNotFoundError("document not found")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class TestKnowledgeSchemas:
    def test_document_format_enum(self):
        assert DocumentFormat.TXT.value == "txt"
        assert DocumentFormat.PDF.value == "pdf"

    def test_chunking_strategy_enum(self):
        assert ChunkingStrategy.FIXED.value == "fixed"
        assert ChunkingStrategy.SLIDING_WINDOW.value == "sliding_window"

    def test_document_status_enum(self):
        assert DocumentStatus.PENDING.value == "pending"
        assert DocumentStatus.COMPLETED.value == "completed"
        assert DocumentStatus.FAILED.value == "failed"

    def test_chunk_metadata_defaults(self):
        from app.ai.knowledge.schemas.schemas import ChunkMetadata
        m = ChunkMetadata(source_document="doc1", chunk_index=0)
        assert m.heading_path == []
        assert m.char_start == 0
        assert m.word_count == 0

    def test_document_chunk_creation(self):
        chunk = DocumentChunk(
            id="chunk_1",
            content="test content",
            metadata={"source_document": "doc1", "chunk_index": 0},
        )
        assert chunk.id == "chunk_1"
        assert chunk.content == "test content"

    def test_processing_config_defaults(self):
        cfg = ProcessingConfig()
        assert cfg.chunk_size == 500
        assert cfg.chunk_overlap == 50
        assert cfg.chunking_strategy == ChunkingStrategy.PARAGRAPH
        assert cfg.skip_parsing is False
        assert len(cfg.allowed_formats) == 7

    def test_catalog_entry_creation(self):
        entry = CatalogEntry(
            id="doc_1",
            filename="test.txt",
            format=DocumentFormat.TXT,
            size_bytes=100,
            status=DocumentStatus.COMPLETED,
            version=1,
            metadata=DocumentMetadata(title="Test"),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        assert entry.filename == "test.txt"
        assert entry.metadata.title == "Test"

    def test_document_metadata_defaults(self):
        m = DocumentMetadata()
        assert m.title == ""
        assert m.tags == []


# ---------------------------------------------------------------------------
# Utils
# ---------------------------------------------------------------------------

class TestKnowledgeUtils:
    def test_generate_document_id(self):
        doc_id = generate_document_id()
        assert doc_id.startswith("doc_")
        assert len(doc_id) > 10

    def test_compute_checksum(self):
        c1 = compute_checksum(b"hello world")
        c2 = compute_checksum(b"hello world")
        c3 = compute_checksum(b"different")
        assert c1 == c2
        assert c1 != c3
        assert len(c1) == 16


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

class TestLoaders:
    @pytest.mark.asyncio
    async def test_text_loader(self):
        loader = TextLoader()
        file = io.BytesIO(b"hello world")
        content = await loader.load(file, DocumentFormat.TXT)
        assert content == "hello world"
        assert DocumentFormat.TXT in loader.supported_formats()
        assert DocumentFormat.MD in loader.supported_formats()

    @pytest.mark.asyncio
    async def test_csv_loader(self):
        loader = CSVLoader()
        file = io.BytesIO(b"name,age\nAlice,30\nBob,25")
        content = await loader.load(file, DocumentFormat.CSV)
        assert "name | age" in content
        assert "Alice | 30" in content

    @pytest.mark.asyncio
    async def test_json_loader(self):
        loader = JSONLoader()
        data = json.dumps({"key": "value"}).encode()
        file = io.BytesIO(data)
        content = await loader.load(file, DocumentFormat.JSON)
        assert '"key"' in content
        assert '"value"' in content

    @pytest.mark.asyncio
    async def test_html_loader_strips_tags(self):
        loader = HTMLLoader()
        html = b"<html><body><p>Hello <b>World</b></p></body></html>"
        file = io.BytesIO(html)
        content = await loader.load(file, DocumentFormat.HTML)
        assert "Hello" in content
        assert "World" in content
        assert "<b>" not in content

    @pytest.mark.asyncio
    async def test_html_loader_removes_script(self):
        loader = HTMLLoader()
        html = b"<html><script>alert('x')</script><body>text</body></html>"
        file = io.BytesIO(html)
        content = await loader.load(file, DocumentFormat.HTML)
        assert "alert" not in content
        assert "text" in content

    @pytest.mark.asyncio
    async def test_pdf_loader_fallback(self):
        loader = PDFLoader()
        file = io.BytesIO(b"%PDF-1.4 junk content")
        content = await loader.load(file, DocumentFormat.PDF)
        assert "PDF document" in content
        assert "bytes" in content

    @pytest.mark.asyncio
    async def test_docx_loader_fallback(self):
        loader = DOCXLoader()
        file = io.BytesIO(b"fake docx content")
        content = await loader.load(file, DocumentFormat.DOCX)
        assert "DOCX document" in content

    def test_loader_factory(self):
        loader = LoaderFactory.get_loader(DocumentFormat.TXT)
        assert isinstance(loader, TextLoader)
        loader2 = LoaderFactory.get_loader(DocumentFormat.TXT)
        assert loader is loader2

    def test_loader_factory_unsupported(self):
        from app.ai.knowledge.exceptions.exceptions import UnsupportedFormatError
        with pytest.raises(UnsupportedFormatError):
            LoaderFactory.get_loader("unknown")


# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

class TestParsers:
    @pytest.mark.asyncio
    async def test_parse_returns_stripped_content(self):
        parser = DocumentParser()
        result = await parser.parse("  hello world  ", DocumentFormat.TXT)
        assert result == "hello world"

    @pytest.mark.asyncio
    async def test_extract_headings_markdown(self):
        parser = DocumentParser()
        content = "# Title\n\nSome text\n## Subtitle\n\nMore text"
        headings = await parser.extract_headings(content)
        assert len(headings) >= 1
        assert any("Title" in h[0] for h in headings)

    @pytest.mark.asyncio
    async def test_extract_paragraphs(self):
        parser = DocumentParser()
        content = "Para one.\n\nPara two.\n\nPara three."
        paragraphs = await parser.extract_paragraphs(content)
        assert len(paragraphs) == 3
        assert paragraphs[0] == "Para one."


# ---------------------------------------------------------------------------
# Normalizers
# ---------------------------------------------------------------------------

class TestNormalizers:
    @pytest.mark.asyncio
    async def test_whitespace_normalizer(self):
        n = WhitespaceNormalizer()
        result = await n.normalize("Hello   World\r\n\r\n\r\nTest")
        assert "Hello World" in result
        assert "\r" not in result

    @pytest.mark.asyncio
    async def test_unicode_normalizer(self):
        n = UnicodeNormalizer()
        result = await n.normalize("\u2018quotes\u2019")
        assert "\u2018quotes\u2019" in result

    @pytest.mark.asyncio
    async def test_quote_normalizer(self):
        n = QuoteNormalizer()
        result = await n.normalize("\u201cHello\u201d \u2014 world")
        assert '"' in result
        assert "--" in result
        assert "\u201c" not in result

    @pytest.mark.asyncio
    async def test_composite_normalizer(self):
        n = CompositeNormalizer([WhitespaceNormalizer(), QuoteNormalizer()])
        result = await n.normalize("  \u201cHello\u201d  ")
        assert result == '"Hello"'


# ---------------------------------------------------------------------------
# Cleaners
# ---------------------------------------------------------------------------

class TestCleaners:
    @pytest.mark.asyncio
    async def test_boilerplate_remover_copyright(self):
        c = BoilerplateRemover()
        result = await c.clean("Hello\nCopyright 2024 Acme Corp\nWorld")
        assert "Copyright" not in result

    @pytest.mark.asyncio
    async def test_boilerplate_remover_disclaimer(self):
        c = BoilerplateRemover()
        result = await c.clean("Content\nDisclaimer: This is confidential\nMore")
        assert "Disclaimer" not in result

    @pytest.mark.asyncio
    async def test_header_footer_stripper(self):
        c = HeaderFooterStripper()
        text = "\n".join([f"Line {i}" for i in range(10)])
        result = await c.clean(text)
        lines = result.split("\n")
        assert len(lines) < 10

    @pytest.mark.asyncio
    async def test_composite_cleaner(self):
        c = CompositeCleaner([BoilerplateRemover()])
        result = await c.clean("Text\nCopyright 2024\nEnd")
        assert "Copyright" not in result


# ---------------------------------------------------------------------------
# Metadata Extractor
# ---------------------------------------------------------------------------

class TestMetadataExtractor:
    @pytest.mark.asyncio
    async def test_extract_title_from_markdown(self):
        ex = DefaultMetadataExtractor()
        meta = await ex.extract("# My Title\n\nContent", "test.md")
        assert meta.title == "My Title"

    @pytest.mark.asyncio
    async def test_extract_title_from_filename(self):
        ex = DefaultMetadataExtractor()
        meta = await ex.extract("plain content", "my_document.txt")
        assert "My Document" in meta.title

    @pytest.mark.asyncio
    async def test_extract_author_from_content(self):
        ex = DefaultMetadataExtractor()
        meta = await ex.extract("Author: Dr. Smith\nContent here", "test.txt")
        assert "Dr. Smith" in meta.author

    @pytest.mark.asyncio
    async def test_extract_specialty(self):
        ex = DefaultMetadataExtractor()
        meta = await ex.extract("This is about cardiology and heart", "test.txt")
        assert meta.specialty == "cardiology"

    @pytest.mark.asyncio
    async def test_extract_tags(self):
        ex = DefaultMetadataExtractor()
        meta = await ex.extract("Tags: heart, cardiology, surgery\nContent", "test.txt")
        assert "heart" in meta.tags
        assert "cardiology" in meta.tags


# ---------------------------------------------------------------------------
# Chunkers
# ---------------------------------------------------------------------------

class TestChunkers:
    @pytest.mark.asyncio
    async def test_fixed_size_chunker(self):
        chunker = FixedSizeChunker()
        content = "Hello world. " * 50
        config = ProcessingConfig(chunk_size=50, chunk_overlap=10)
        chunks = await chunker.chunk(content, config)
        assert len(chunks) > 1
        assert all(isinstance(c, DocumentChunk) for c in chunks)

    @pytest.mark.asyncio
    async def test_paragraph_chunker(self):
        chunker = ParagraphChunker()
        content = "Para one.\n\nPara two.\n\nPara three.\n\nPara four.\n\nPara five."
        config = ProcessingConfig(chunk_size=20, chunk_overlap=0)
        chunks = await chunker.chunk(content, config)
        assert len(chunks) > 0

    @pytest.mark.asyncio
    async def test_heading_aware_chunker(self):
        chunker = HeadingAwareChunker()
        content = "# Section 1\n\nContent 1\n\n## Sub 1\n\nSub content\n\n# Section 2\n\nContent 2"
        config = ProcessingConfig(chunk_size=1000, chunk_overlap=0)
        parser = DocumentParser()
        headings = await parser.extract_headings(content)
        chunks = await chunker.chunk(content, config, headings)
        assert len(chunks) >= 2

    @pytest.mark.asyncio
    async def test_sliding_window_chunker(self):
        chunker = SlidingWindowChunker()
        content = "word " * 100
        config = ProcessingConfig(chunk_size=20, chunk_overlap=5)
        chunks = await chunker.chunk(content, config)
        assert len(chunks) > 1

    def test_chunker_factory(self):
        c1 = ChunkerFactory.get_chunker("paragraph")
        c2 = ChunkerFactory.get_chunker("paragraph")
        assert isinstance(c1, ParagraphChunker)
        assert c1 is c2

    def test_chunker_factory_unknown_defaults(self):
        c = ChunkerFactory.get_chunker("unknown")
        assert isinstance(c, ParagraphChunker)


# ---------------------------------------------------------------------------
# Validators
# ---------------------------------------------------------------------------

class TestValidators:
    @pytest.mark.asyncio
    async def test_validate_format_valid(self):
        v = DocumentValidator()
        result = await v.validate_format("test.txt", DocumentFormat.TXT)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_format_invalid(self):
        v = DocumentValidator()
        with pytest.raises(UnsupportedFormatError):
            await v.validate_format("test.txt", DocumentFormat.PDF)

    @pytest.mark.asyncio
    async def test_validate_size_ok(self):
        v = DocumentValidator()
        result = await v.validate_size(100, 10)
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_size_exceeded(self):
        v = DocumentValidator()
        with pytest.raises(FileSizeExceededError):
            await v.validate_size(100 * 1024 * 1024, 1)

    @pytest.mark.asyncio
    async def test_validate_encoding_utf8(self):
        v = DocumentValidator()
        result = await v.validate_encoding("hello".encode("utf-8"))
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_encoding_invalid(self):
        v = DocumentValidator()
        with pytest.raises(EncodingError):
            await v.validate_encoding(b"\xff\xfe\x00\x01")

    @pytest.mark.asyncio
    async def test_validate_content_quality_empty(self):
        v = DocumentValidator()
        ok, err = await v.validate_content_quality("")
        assert ok is False
        assert err is not None

    @pytest.mark.asyncio
    async def test_validate_content_quality_ok(self):
        v = DocumentValidator()
        ok, err = await v.validate_content_quality("Valid content here")
        assert ok is True
        assert err is None

    def test_compute_checksum(self):
        v = DocumentValidator()
        c1 = v.compute_checksum(b"hello")
        c2 = v.compute_checksum(b"hello")
        assert c1 == c2
        assert len(c1) == 16


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class TestStorage:
    @pytest.mark.asyncio
    async def test_store_and_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            doc = KnowledgeDocument(
                id="doc_test_1",
                filename="test.txt",
                format=DocumentFormat.TXT,
                size_bytes=100,
                checksum="abc123",
                status=DocumentStatus.COMPLETED,
                version=1,
                metadata=DocumentMetadata(title="Test"),
                chunks=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            path = await storage.store(doc)
            assert os.path.exists(path)

            retrieved = await storage.retrieve("doc_test_1")
            assert retrieved is not None
            assert retrieved.id == "doc_test_1"
            assert retrieved.filename == "test.txt"
            assert retrieved.metadata.title == "Test"

    @pytest.mark.asyncio
    async def test_retrieve_not_found(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            result = await storage.retrieve("nonexistent")
            assert result is None

    @pytest.mark.asyncio
    async def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            doc = KnowledgeDocument(
                id="doc_del", filename="d.txt", format=DocumentFormat.TXT,
                size_bytes=10, checksum="x", status=DocumentStatus.COMPLETED,
                version=1, metadata=DocumentMetadata(), chunks=[],
                created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
            )
            await storage.store(doc)
            assert await storage.document_exists("doc_del") is True
            deleted = await storage.delete("doc_del")
            assert deleted is True
            assert await storage.document_exists("doc_del") is False

    @pytest.mark.asyncio
    async def test_list_documents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=tmpdir)
            doc1 = KnowledgeDocument(
                id="doc_a", filename="a.txt", format=DocumentFormat.TXT,
                size_bytes=10, checksum="x", status=DocumentStatus.COMPLETED,
                version=1, metadata=DocumentMetadata(), chunks=[],
                created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
            )
            doc2 = KnowledgeDocument(
                id="doc_b", filename="b.txt", format=DocumentFormat.TXT,
                size_bytes=20, checksum="y", status=DocumentStatus.COMPLETED,
                version=1, metadata=DocumentMetadata(), chunks=[],
                created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
            )
            await storage.store(doc1)
            await storage.store(doc2)
            ids = await storage.list_documents()
            assert "doc_a" in ids
            assert "doc_b" in ids


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

class TestCatalog:
    def test_add_and_get_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog_path = os.path.join(tmpdir, "catalog.json")
            catalog = KnowledgeCatalog(catalog_path=catalog_path)
            entry = CatalogEntry(
                id="doc_1", filename="t.txt", format=DocumentFormat.TXT,
                size_bytes=100, status=DocumentStatus.COMPLETED, version=1,
                metadata=DocumentMetadata(), created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            catalog.add_entry(entry)
            retrieved = catalog.get_entry("doc_1")
            assert retrieved is not None
            assert retrieved.id == "doc_1"

    def test_update_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "c.json"))
            entry = CatalogEntry(
                id="doc_1", filename="t.txt", format=DocumentFormat.TXT,
                size_bytes=100, status=DocumentStatus.PENDING, version=1,
                metadata=DocumentMetadata(), created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            catalog.add_entry(entry)
            updated = catalog.update_entry("doc_1", status=DocumentStatus.COMPLETED)
            assert updated is not None
            assert updated.status == DocumentStatus.COMPLETED

    def test_remove_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "c.json"))
            entry = CatalogEntry(
                id="doc_1", filename="t.txt", format=DocumentFormat.TXT,
                size_bytes=100, status=DocumentStatus.COMPLETED, version=1,
                metadata=DocumentMetadata(), created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            catalog.add_entry(entry)
            assert catalog.remove_entry("doc_1") is True
            assert catalog.get_entry("doc_1") is None

    def test_list_entries(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "c.json"))
            for i in range(5):
                catalog.add_entry(CatalogEntry(
                    id=f"doc_{i}", filename=f"{i}.txt", format=DocumentFormat.TXT,
                    size_bytes=100, status=DocumentStatus.COMPLETED, version=1,
                    metadata=DocumentMetadata(), created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc),
                ))
            entries = catalog.list_entries(limit=3)
            assert len(entries) == 3


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class TestPipeline:
    @pytest.mark.asyncio
    async def test_pipeline_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=os.path.join(tmpdir, "docs"))
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "catalog.json"))
            pipeline = ProcessingPipeline(storage=storage, catalog=catalog)
            content = b"# Test Title\n\nThis is some test content for the pipeline."
            file = io.BytesIO(content)
            result = await pipeline.run(file, "test.md", content)
            assert result.success is True
            assert result.document_id is not None
            assert len(result.stages) > 0
            stored = await storage.retrieve(result.document_id)
            assert stored is not None
            assert stored.status == DocumentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_pipeline_empty_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=os.path.join(tmpdir, "docs"))
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "catalog.json"))
            pipeline = ProcessingPipeline(storage=storage, catalog=catalog)
            content = b""
            file = io.BytesIO(content)
            result = await pipeline.run(file, "empty.txt", content)
            assert result.success is False

    @pytest.mark.asyncio
    async def test_pipeline_sequence(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=os.path.join(tmpdir, "docs"))
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "catalog.json"))
            pipeline = ProcessingPipeline(storage=storage, catalog=catalog)
            content = b"Valid document content for testing pipeline stages."
            file = io.BytesIO(content)
            result = await pipeline.run(file, "test.txt", content)
            stage_names = [s.stage for s in result.stages]
            assert "import" in stage_names
            assert "parse" in stage_names
            assert "chunk" in stage_names
            assert "store" in stage_names


# ---------------------------------------------------------------------------
# KnowledgeService
# ---------------------------------------------------------------------------

class TestKnowledgeService:
    @pytest.mark.asyncio
    async def test_import_and_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=os.path.join(tmpdir, "docs"))
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "catalog.json"))
            service = KnowledgeService(storage=storage, catalog=catalog)
            file = io.BytesIO(b"# Hello\n\nWorld content here.")
            result = await service.import_document(file, "hello.md")
            assert result.status == DocumentStatus.COMPLETED
            assert result.document_id is not None
            assert result.chunk_count > 0

            doc = await service.get_document(result.document_id)
            assert doc is not None
            assert doc.filename == "hello.md"

    @pytest.mark.asyncio
    async def test_list_documents(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=os.path.join(tmpdir, "docs"))
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "catalog.json"))
            service = KnowledgeService(storage=storage, catalog=catalog)
            await service.import_document(io.BytesIO(b"This is document A with enough content."), "a.txt")
            await service.import_document(io.BytesIO(b"This is document B with enough content."), "b.txt")
            entries, total = await service.list_documents()
            assert total >= 2

    @pytest.mark.asyncio
    async def test_delete_document(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=os.path.join(tmpdir, "docs"))
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "catalog.json"))
            service = KnowledgeService(storage=storage, catalog=catalog)
            result = await service.import_document(io.BytesIO(b"This is a longer document content for testing."), "del.txt")
            doc_id = result.document_id
            assert await service.document_exists(doc_id) is True
            deleted = await service.delete_document(doc_id)
            assert deleted is True
            assert await service.document_exists(doc_id) is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=os.path.join(tmpdir, "docs"))
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "catalog.json"))
            service = KnowledgeService(storage=storage, catalog=catalog)
            deleted = await service.delete_document("nonexistent")
            assert deleted is False

    @pytest.mark.asyncio
    async def test_import_unsupported_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=os.path.join(tmpdir, "docs"))
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "catalog.json"))
            service = KnowledgeService(storage=storage, catalog=catalog)
            result = await service.import_document(io.BytesIO(b"data"), "file.xyz")
            assert result.status == DocumentStatus.FAILED


# ---------------------------------------------------------------------------
# DI / Deps
# ---------------------------------------------------------------------------

class TestKnowledgeDeps:
    def test_reset_knowledge_service(self):
        reset_knowledge_service()
        assert get_knowledge_service() is not None

    def test_set_and_get(self):
        reset_knowledge_service()
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=os.path.join(tmpdir, "docs"))
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "catalog.json"))
            mock_service = KnowledgeService(storage=storage, catalog=catalog)
            set_knowledge_service(mock_service)
            assert get_knowledge_service() is mock_service
            reset_knowledge_service()


# ---------------------------------------------------------------------------
# Integration via API
# ---------------------------------------------------------------------------

class TestKnowledgeAPI:
    @pytest.mark.asyncio
    async def test_import_endpoint(self):
        from app.main import app
        from fastapi.testclient import TestClient
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalFileStorage(base_path=os.path.join(tmpdir, "docs"))
            catalog = KnowledgeCatalog(catalog_path=os.path.join(tmpdir, "catalog.json"))
            service = KnowledgeService(storage=storage, catalog=catalog)
            set_knowledge_service(service)
            client = TestClient(app)
            response = client.post(
                "/ai/knowledge/import",
                files={"file": ("test.txt", b"Hello World Content", "text/plain")},
                headers={"Authorization": "Bearer test_token"},
            )
            reset_knowledge_service()
            assert response.status_code in (200, 201, 401, 403)
