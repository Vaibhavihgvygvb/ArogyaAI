import hashlib

from app.ai.embeddings.interfaces.interfaces import EmbeddingProvider
from app.ai.embeddings.schemas.schemas import EmbeddingProviderType


class MockEmbeddingProvider(EmbeddingProvider):
    _dimension: int = 384
    _default_model: str = "mock-embedding-v1"
    _supported_models: list[str] = ["mock-embedding-v1", "mock-large-v2"]

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        result = []
        for text in texts:
            seed = hashlib.md5(text.encode()).digest()
            vector = [((seed[i % 16] + hash(text)) % 256) / 255.0 for i in range(self._dimension)]
            magnitude = sum(v * v for v in vector) ** 0.5
            if magnitude > 0:
                vector = [v / magnitude for v in vector]
            result.append(vector)
        return result

    def provider_type(self) -> EmbeddingProviderType:
        return EmbeddingProviderType.MOCK

    def default_model(self) -> str:
        return self._default_model

    def dimensions(self) -> int:
        return self._dimension

    def supported_models(self) -> list[str]:
        return self._supported_models
