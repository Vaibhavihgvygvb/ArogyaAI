from abc import ABC, abstractmethod
from typing import IO

from app.ai.knowledge.schemas.schemas import (
    DocumentChunk,
    DocumentFormat,
    DocumentMetadata,
    KnowledgeDocument,
    ProcessingConfig,
)


class Loader(ABC):
    @abstractmethod
    async def load(self, file: IO, format: DocumentFormat) -> str:
        pass

    @abstractmethod
    def supported_formats(self) -> list[DocumentFormat]:
        pass


class Parser(ABC):
    @abstractmethod
    async def parse(self, content: str, format: DocumentFormat) -> str:
        pass

    @abstractmethod
    async def extract_headings(self, content: str) -> list[tuple[str, int]]:
        pass

    @abstractmethod
    async def extract_paragraphs(self, content: str) -> list[str]:
        pass


class Normalizer(ABC):
    @abstractmethod
    async def normalize(self, content: str) -> str:
        pass


class Cleaner(ABC):
    @abstractmethod
    async def clean(self, content: str) -> str:
        pass


class MetadataExtractor(ABC):
    @abstractmethod
    async def extract(self, content: str, filename: str) -> DocumentMetadata:
        pass


class Chunker(ABC):
    @abstractmethod
    async def chunk(
        self,
        content: str,
        config: ProcessingConfig,
        headings: list[tuple[str, int]] | None = None,
    ) -> list[DocumentChunk]:
        pass

    @abstractmethod
    def strategy(self) -> str:
        pass


class Validator(ABC):
    @abstractmethod
    async def validate_format(self, filename: str, format: DocumentFormat) -> bool:
        pass

    @abstractmethod
    async def validate_size(self, size_bytes: int, max_size_mb: int) -> bool:
        pass

    @abstractmethod
    async def validate_encoding(self, content: bytes) -> bool:
        pass

    @abstractmethod
    async def validate_content_quality(self, content: str) -> tuple[bool, str | None]:
        pass


class StorageProvider(ABC):
    @abstractmethod
    async def store(self, document: KnowledgeDocument) -> str:
        pass

    @abstractmethod
    async def retrieve(self, document_id: str) -> KnowledgeDocument | None:
        pass

    @abstractmethod
    async def delete(self, document_id: str) -> bool:
        pass

    @abstractmethod
    async def list_documents(self) -> list[str]:
        pass

    @abstractmethod
    async def document_exists(self, document_id: str) -> bool:
        pass
