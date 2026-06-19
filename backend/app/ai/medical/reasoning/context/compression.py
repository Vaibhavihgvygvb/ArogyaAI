from app.ai.medical.reasoning.exceptions.exceptions import ContextCompressionError
from app.ai.medical.reasoning.interfaces.interfaces import (
    RETRIEVAL_RESULT_TYPE,
    ContextCompressorABC,
)
from app.ai.medical.reasoning.schemas.schemas import (
    CompressedContext,
    CompressionStrategy,
    RankedContext,
)


class ContextCompressor(ContextCompressorABC):
    async def compress(
        self,
        results: list[RETRIEVAL_RESULT_TYPE],
        ranked_context: RankedContext,
        query: str,
        max_tokens: int,
    ) -> CompressedContext:
        if not results:
            return CompressedContext(
                context="",
                original_token_count=0,
                compressed_token_count=0,
                compression_ratio=0.0,
                removed_chunk_ids=[],
                strategy=CompressionStrategy.NONE,
            )

        chunk_map = self._build_chunk_map(results)
        ordered_chunks = self._order_by_rank(chunk_map, ranked_context)
        max_chars = max_tokens * 4

        original_text = "\n\n".join(
            f"[Source {i + 1}]:\n{c['content']}"
            for i, c in enumerate(ordered_chunks)
        )
        original_tokens = len(original_text) // 4

        if original_tokens <= max_tokens:
            return CompressedContext(
                context=original_text,
                original_token_count=original_tokens,
                compressed_token_count=original_tokens,
                compression_ratio=0.0,
                removed_chunk_ids=[],
                strategy=CompressionStrategy.NONE,
            )

        compressed_parts: list[str] = []
        compressed_ids: list[str] = []
        removed_ids: list[str] = []
        current_chars = 0

        for chunk in ordered_chunks:
            chunk_text = chunk["content"]
            chunk_with_header = f"[Source {len(compressed_parts) + 1}]:\n{chunk_text}"
            chunk_len = len(chunk_with_header) + 2

            if current_chars + chunk_len <= max_chars:
                compressed_parts.append(chunk_with_header)
                compressed_ids.append(chunk["id"])
                current_chars += chunk_len
            else:
                remaining = max_chars - current_chars
                if remaining > 20 or not compressed_parts:
                    truncated = chunk_text[:max(remaining, 10)]
                    compressed_parts.append(f"[Source {len(compressed_parts) + 1}]:\n{truncated}...[truncated]")
                    compressed_ids.append(chunk["id"])
                    current_chars += len(truncated)
                removed_ids.append(chunk["id"])

        compressed_text = "\n\n".join(compressed_parts)
        compressed_tokens = len(compressed_text) // 4
        ratio = round(1 - (compressed_tokens / original_tokens), 4) if original_tokens > 0 else 0.0

        return CompressedContext(
            context=compressed_text,
            original_token_count=original_tokens,
            compressed_token_count=compressed_tokens,
            compression_ratio=ratio,
            removed_chunk_ids=removed_ids,
            strategy=CompressionStrategy.EXTRACTIVE,
        )

    def _build_chunk_map(self, results: list[RETRIEVAL_RESULT_TYPE]) -> dict[str, dict]:
        chunk_map: dict[str, dict] = {}
        for r in results:
            chunk_id = getattr(r, "chunk_id", "") or str(id(r))
            content = getattr(r, "content", "") or getattr(r, "evidence_text", "") or ""
            chunk_map[chunk_id] = {
                "id": chunk_id,
                "content": content,
                "knowledge_id": getattr(r, "knowledge_id", "") or "",
                "score": getattr(r, "score", 0) or 0,
            }
        return chunk_map

    def _order_by_rank(self, chunk_map: dict[str, dict], ranked_context: RankedContext) -> list[dict]:
        ordered = []
        seen: set[str] = set()

        for cid in ranked_context.chunk_ids:
            if cid in chunk_map and cid not in seen:
                ordered.append(chunk_map[cid])
                seen.add(cid)

        for cid, chunk in chunk_map.items():
            if cid not in seen:
                ordered.append(chunk)
                seen.add(cid)

        return ordered
