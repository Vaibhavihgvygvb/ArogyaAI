import hashlib
import os
import time
import uuid
from datetime import datetime, timezone


def generate_document_id() -> str:
    return f"doc_{uuid.uuid4().hex[:24]}"


def compute_checksum(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:16]


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()


def timing_ms(start: float) -> float:
    return round((time.time() - start) * 1000, 2)
