import hashlib
import time
import uuid


def generate_query_id() -> str:
    return f"qry_{uuid.uuid4().hex[:24]}"


def timing_ms(start: float) -> float:
    return round((time.time() - start) * 1000, 2)


def compute_query_hash(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)
