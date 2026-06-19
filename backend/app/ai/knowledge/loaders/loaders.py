import csv
import io
import json
import os
from typing import IO

from app.ai.knowledge.exceptions.exceptions import UnsupportedFormatError
from app.ai.knowledge.interfaces.interfaces import Loader
from app.ai.knowledge.schemas.schemas import DocumentFormat


class TextLoader(Loader):
    async def load(self, file: IO, format: DocumentFormat) -> str:
        raw = file.read()
        if isinstance(raw, bytes):
            return raw.decode("utf-8")
        return raw

    def supported_formats(self) -> list[DocumentFormat]:
        return [DocumentFormat.TXT, DocumentFormat.MD]


class CSVParser:
    @staticmethod
    def to_text(content: str) -> str:
        lines = []
        reader = csv.reader(io.StringIO(content))
        for row in reader:
            lines.append(" | ".join(row))
        return "\n".join(lines)


class CSVLoader(Loader):
    async def load(self, file: IO, format: DocumentFormat) -> str:
        raw = file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return CSVParser.to_text(raw)

    def supported_formats(self) -> list[DocumentFormat]:
        return [DocumentFormat.CSV]


class JSONLoader(Loader):
    async def load(self, file: IO, format: DocumentFormat) -> str:
        raw = file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        data = json.loads(raw)
        return json.dumps(data, indent=2, ensure_ascii=False)

    def supported_formats(self) -> list[DocumentFormat]:
        return [DocumentFormat.JSON]


class HTMLLoader(Loader):
    async def load(self, file: IO, format: DocumentFormat) -> str:
        raw = file.read()
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        return self._strip_html_tags(raw)

    def _strip_html_tags(self, html: str) -> str:
        import re
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def supported_formats(self) -> list[DocumentFormat]:
        return [DocumentFormat.HTML]


class PDFLoader(Loader):
    async def load(self, file: IO, format: DocumentFormat) -> str:
        raw = file.read()
        if not isinstance(raw, bytes):
            raw = raw.encode("utf-8")
        try:
            import PyPDF2
            reader = PyPDF2.PdfReader(io.BytesIO(raw))
            pages = []
            for page in reader.pages:
                pages.append(page.extract_text())
            return "\n\n".join(pages)
        except ImportError:
            pass
        try:
            import pdfplumber
            pages = []
            with pdfplumber.open(io.BytesIO(raw)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text()
                    if text:
                        pages.append(text)
            return "\n\n".join(pages)
        except ImportError:
            pass
        try:
            import pdfminer
            from pdfminer.high_level import extract_text as pdfminer_extract
            return pdfminer_extract(io.BytesIO(raw))
        except ImportError:
            pass
        return f"[PDF document: {len(raw)} bytes - install PyPDF2 or pdfplumber for text extraction]"

    def supported_formats(self) -> list[DocumentFormat]:
        return [DocumentFormat.PDF]


class DOCXLoader(Loader):
    async def load(self, file: IO, format: DocumentFormat) -> str:
        raw = file.read()
        if not isinstance(raw, bytes):
            raw = raw.encode("utf-8")
        try:
            from docx import Document
            doc = Document(io.BytesIO(raw))
            paragraphs = [p.text for p in doc.paragraphs]
            return "\n\n".join(paragraphs)
        except ImportError:
            pass
        return f"[DOCX document: {len(raw)} bytes - install python-docx for text extraction]"

    def supported_formats(self) -> list[DocumentFormat]:
        return [DocumentFormat.DOCX]


class LoaderFactory:
    _loaders: dict[DocumentFormat, Loader] = {}

    @classmethod
    def get_loader(cls, format: DocumentFormat) -> Loader:
        if format not in cls._loaders:
            loader = cls._create_loader(format)
            cls._loaders[format] = loader
        return cls._loaders[format]

    @classmethod
    def _create_loader(cls, format: DocumentFormat) -> Loader:
        match format:
            case DocumentFormat.TXT | DocumentFormat.MD:
                return TextLoader()
            case DocumentFormat.CSV:
                return CSVLoader()
            case DocumentFormat.JSON:
                return JSONLoader()
            case DocumentFormat.HTML:
                return HTMLLoader()
            case DocumentFormat.PDF:
                return PDFLoader()
            case DocumentFormat.DOCX:
                return DOCXLoader()
            case _:
                raise UnsupportedFormatError(f"No loader for format: {format}")
