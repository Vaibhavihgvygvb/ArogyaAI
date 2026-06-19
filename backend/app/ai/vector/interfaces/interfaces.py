from abc import ABC, abstractmethod


class VectorStoreProvider(ABC):
    @abstractmethod
    async def add(self, embedding_id: str, vector: list[float], metadata: dict | None = None) -> str:
        pass

    @abstractmethod
    async def add_batch(self, vectors: list[tuple[str, list[float], dict | None]]) -> list[str]:
        pass

    @abstractmethod
    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[dict]:
        pass

    @abstractmethod
    async def delete(self, embedding_id: str) -> bool:
        pass

    @abstractmethod
    async def delete_by_filter(self, filters: dict) -> int:
        pass

    @abstractmethod
    async def count(self) -> int:
        pass

    @abstractmethod
    async def clear(self) -> None:
        pass

    @abstractmethod
    def provider_name(self) -> str:
        pass
