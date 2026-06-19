from typing import AsyncGenerator

from app.ai.medical.response.exceptions.exceptions import StreamingError
from app.ai.medical.response.schemas.schemas import StreamChunk

CHUNK_SEPARATOR = " "
MIN_CHUNK_SIZE = 10


class StreamingHandler:
    def __init__(self, chunk_size: int = 50):
        if chunk_size < 1:
            raise StreamingError("chunk_size must be >= 1")
        self._chunk_size = chunk_size

    async def stream_text(self, text: str) -> AsyncGenerator[StreamChunk, None]:
        if not text:
            yield StreamChunk(content="", done=True)
            return

        words = text.split(CHUNK_SEPARATOR)
        buffer: list[str] = []
        char_count = 0
        chunk_index = 0

        for word in words:
            buffer.append(word)
            char_count += len(word) + 1

            if char_count >= self._chunk_size:
                content = CHUNK_SEPARATOR.join(buffer)
                yield StreamChunk(content=content, done=False, chunk_index=chunk_index)
                buffer = []
                char_count = 0
                chunk_index += 1

        if buffer:
            remaining = CHUNK_SEPARATOR.join(buffer)
            if remaining.strip():
                yield StreamChunk(content=remaining, done=False, chunk_index=chunk_index)

        yield StreamChunk(content="", done=True, chunk_index=chunk_index + 1)

    async def stream_sections(
        self,
        section_texts: list[tuple[str, str]],
    ) -> AsyncGenerator[StreamChunk, None]:
        chunk_index = 0
        for title, content in section_texts:
            header = f"## {title}\n\n"
            yield StreamChunk(content=header, done=False, chunk_index=chunk_index)
            chunk_index += 1

            async for chunk in self.stream_text(content):
                if not chunk.done:
                    yield StreamChunk(content=chunk.content, done=False, chunk_index=chunk_index)
                    chunk_index += 1

            yield StreamChunk(content="\n\n", done=False, chunk_index=chunk_index)
            chunk_index += 1

        yield StreamChunk(content="", done=True, chunk_index=chunk_index)

    def estimate_chunks(self, text: str) -> int:
        if not text:
            return 1
        words = text.split(CHUNK_SEPARATOR)
        total_chars = sum(len(w) + 1 for w in words)
        return max(1, total_chars // self._chunk_size) + 1
