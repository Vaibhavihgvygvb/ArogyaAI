import hashlib
import time
import uuid


def generate_embedding_id() -> str:
    return f"emb_{uuid.uuid4().hex[:24]}"


def generate_batch_id() -> str:
    return f"batch_{uuid.uuid4().hex[:24]}"


def compute_content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]


def compute_vector_checksum(vector: list[float]) -> str:
    raw = ",".join(f"{v:.6f}" for v in vector[:100])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def timing_ms(start: float) -> float:
    return round((time.time() - start) * 1000, 2)


def chunk_text_for_embedding(content: str, max_chars: int = 8192) -> str:
    if len(content) > max_chars:
        return content[:max_chars]
    return content


def validate_vector_dimension(vector: list[float], expected: int) -> bool:
    return len(vector) == expected


def normalize_vector(vector: list[float]) -> list[float]:
    magnitude = sum(v * v for v in vector) ** 0.5
    if magnitude == 0:
        return vector
    return [v / magnitude for v in vector]
