import hashlib
import re
from typing import Any

from app.ai.knowledge.interfaces.interfaces import Chunker
from app.ai.knowledge.schemas.schemas import ChunkMetadata, ChunkingStrategy, DocumentChunk, ProcessingConfig


class FixedSizeChunker(Chunker):
    def strategy(self) -> str:
        return "fixed"

    async def chunk(
        self,
        content: str,
        config: ProcessingConfig,
        headings: list[tuple[str, int]] | None = None,
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        size = config.chunk_size
        overlap = config.chunk_overlap
        start = 0
        index = 0
        while start < len(content):
            end = min(start + size, len(content))
            chunk_text = content[start:end]
            chunk_id = hashlib.md5(f"{chunk_text[:50]}{index}".encode()).hexdigest()[:12]
            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    content=chunk_text,
                    metadata=ChunkMetadata(
                        source_document="",
                        chunk_index=index,
                        char_start=start,
                        char_end=end,
                        word_count=len(chunk_text.split()),
                    ),
                )
            )
            index += 1
            start += size - overlap
        return chunks


class ParagraphChunker(Chunker):
    def strategy(self) -> str:
        return "paragraph"

    async def chunk(
        self,
        content: str,
        config: ProcessingConfig,
        headings: list[tuple[str, int]] | None = None,
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        paragraphs = re.split(r"\n\s*\n", content.strip())
        current_chunk = ""
        index = 0
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            if len(current_chunk) + len(para) > config.chunk_size and current_chunk:
                chunk_id = hashlib.md5(f"{current_chunk[:50]}{index}".encode()).hexdigest()[:12]
                chunks.append(
                    DocumentChunk(
                        id=chunk_id,
                        content=current_chunk.strip(),
                        metadata=ChunkMetadata(
                            source_document="",
                            chunk_index=index,
                            word_count=len(current_chunk.split()),
                        ),
                    )
                )
                index += 1
                current_chunk = para
            else:
                if current_chunk:
                    current_chunk += "\n\n" + para
                else:
                    current_chunk = para
        if current_chunk:
            chunk_id = hashlib.md5(f"{current_chunk[:50]}{index}".encode()).hexdigest()[:12]
            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    content=current_chunk.strip(),
                    metadata=ChunkMetadata(
                        source_document="",
                        chunk_index=index,
                        word_count=len(current_chunk.split()),
                    ),
                )
            )
        return chunks


class HeadingAwareChunker(Chunker):
    def strategy(self) -> str:
        return "heading_aware"

    async def chunk(
        self,
        content: str,
        config: ProcessingConfig,
        headings: list[tuple[str, int]] | None = None,
    ) -> list[DocumentChunk]:
        if not headings:
            return await ParagraphChunker().chunk(content, config)
        chunks: list[DocumentChunk] = []
        lines = content.split("\n")
        sections: list[tuple[str, int, int]] = []
        heading_lines = {line_num for _, line_num in headings}
        current_heading = ""
        section_start = 0
        for i, line in enumerate(lines):
            if i in heading_lines:
                if current_heading and section_start < i:
                    sections.append((current_heading, section_start, i))
                current_heading = line.strip().lstrip("#").strip()
                section_start = i + 1
        if current_heading and section_start < len(lines):
            sections.append((current_heading, section_start, len(lines)))
        if not sections:
            return await ParagraphChunker().chunk(content, config)
        index = 0
        for heading, start, end in sections:
            section_text = "\n".join(lines[start:end]).strip()
            if not section_text:
                continue
            heading_path = [h for h, _, _ in sections[:sections.index((heading, start, end)) + 1]]
            if len(section_text) <= config.chunk_size:
                chunk_id = hashlib.md5(f"{section_text[:50]}{index}".encode()).hexdigest()[:12]
                chunks.append(
                    DocumentChunk(
                        id=chunk_id,
                        content=section_text,
                        metadata=ChunkMetadata(
                            source_document="",
                            chunk_index=index,
                            heading_path=heading_path,
                            word_count=len(section_text.split()),
                        ),
                    )
                )
                index += 1
            else:
                sub_chunks = await FixedSizeChunker().chunk(section_text, config)
                for sc in sub_chunks:
                    sc.metadata.heading_path = heading_path
                    sc.metadata.chunk_index = index
                    chunks.append(sc)
                    index += 1
        return chunks


class SlidingWindowChunker(Chunker):
    def strategy(self) -> str:
        return "sliding_window"

    async def chunk(
        self,
        content: str,
        config: ProcessingConfig,
        headings: list[tuple[str, int]] | None = None,
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        words = content.split()
        size = config.chunk_size
        overlap = config.chunk_overlap
        index = 0
        for i in range(0, len(words), size - overlap):
            window = words[i : i + size]
            if len(window) < size // 4:
                break
            chunk_text = " ".join(window)
            chunk_id = hashlib.md5(f"{chunk_text[:50]}{index}".encode()).hexdigest()[:12]
            chunks.append(
                DocumentChunk(
                    id=chunk_id,
                    content=chunk_text,
                    metadata=ChunkMetadata(
                        source_document="",
                        chunk_index=index,
                        word_count=len(window),
                    ),
                )
            )
            index += 1
        return chunks


class ChunkerFactory:
    _chunkers: dict[str, Chunker] = {}

    @classmethod
    def get_chunker(cls, strategy: str) -> Chunker:
        key = strategy.lower()
        if key not in cls._chunkers:
            cls._chunkers[key] = cls._create_chunker(key)
        return cls._chunkers[key]

    @classmethod
    def _create_chunker(cls, strategy: str) -> Chunker:
        match strategy:
            case "fixed":
                return FixedSizeChunker()
            case "paragraph":
                return ParagraphChunker()
            case "heading_aware":
                return HeadingAwareChunker()
            case "sliding_window":
                return SlidingWindowChunker()
            case _:
                return ParagraphChunker()
