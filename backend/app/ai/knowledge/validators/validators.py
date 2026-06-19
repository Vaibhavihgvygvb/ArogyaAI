import hashlib
import mimetypes
import os

from app.ai.knowledge.exceptions.exceptions import (
    ChecksumMismatchError,
    ContentQualityError,
    EncodingError,
    FileSizeExceededError,
    UnsupportedFormatError,
)
from app.ai.knowledge.interfaces.interfaces import Validator
from app.ai.knowledge.schemas.schemas import DocumentFormat


class DocumentValidator(Validator):
    _format_map = {
        ".txt": DocumentFormat.TXT,
        ".md": DocumentFormat.MD,
        ".pdf": DocumentFormat.PDF,
        ".docx": DocumentFormat.DOCX,
        ".html": DocumentFormat.HTML,
        ".htm": DocumentFormat.HTML,
        ".csv": DocumentFormat.CSV,
        ".json": DocumentFormat.JSON,
    }

    async def validate_format(self, filename: str, format: DocumentFormat) -> bool:
        ext = os.path.splitext(filename)[1].lower()
        expected = self._format_map.get(ext)
        if expected is None or expected != format:
            raise UnsupportedFormatError(f"Unsupported format or extension mismatch: {filename}")
        return True

    async def validate_size(self, size_bytes: int, max_size_mb: int) -> bool:
        max_bytes = max_size_mb * 1024 * 1024
        if size_bytes > max_bytes:
            raise FileSizeExceededError(
                f"File size {size_bytes} bytes exceeds max {max_bytes} bytes"
            )
        return True

    async def validate_encoding(self, content: bytes) -> bool:
        try:
            content.decode("utf-8")
            return True
        except UnicodeDecodeError:
            raise EncodingError("File is not valid UTF-8")

    async def validate_content_quality(self, content: str) -> tuple[bool, str | None]:
        if not content or not content.strip():
            return False, "Content is empty"
        if len(content.strip()) < 10:
            return False, "Content too short (less than 10 characters)"
        binary_chars = sum(1 for c in content if ord(c) < 8)
        if binary_chars > len(content) * 0.1:
            return False, "Content appears to be binary"
        return True, None

    def compute_checksum(self, content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()[:16]
