from typing import Any

from app.ai.vector.exceptions.exceptions import VectorStoreError
from app.ai.vector.interfaces.interfaces import VectorStoreProvider


class ChromaDBVectorStore(VectorStoreProvider):
    def __init__(
        self,
        collection_name: str = "arogyaai_vectors",
        persist_directory: str | None = None,
    ):
        try:
            import chromadb
        except ImportError:
            raise VectorStoreError("chromadb is not installed. Install with: pip install chromadb")

        self._client = (
            chromadb.PersistentClient(path=persist_directory)
            if persist_directory
            else chromadb.Client()
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    async def add(self, embedding_id: str, vector: list[float], metadata: dict | None = None) -> str:
        try:
            self._collection.add(
                ids=[embedding_id],
                embeddings=[vector],
                metadatas=[metadata or {}],
            )
            return embedding_id
        except Exception as e:
            raise VectorStoreError(f"Failed to add vector to ChromaDB: {e}")

    async def add_batch(self, vectors: list[tuple[str, list[float], dict | None]]) -> list[str]:
        ids = [v[0] for v in vectors]
        embeddings = [v[1] for v in vectors]
        metadatas = [v[2] or {} for v in vectors]
        try:
            self._collection.add(ids=ids, embeddings=embeddings, metadatas=metadatas)
            return ids
        except Exception as e:
            raise VectorStoreError(f"Failed to batch add vectors to ChromaDB: {e}")

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[dict]:
        try:
            where = self._convert_filters(filters) if filters else None
            results = self._collection.query(
                query_embeddings=[query_vector],
                n_results=top_k,
                where=where,
                include=["metadatas", "distances", "embeddings"],
            )
        except Exception as e:
            raise VectorStoreError(f"ChromaDB search failed: {e}")

        if not results["ids"] or not results["ids"][0]:
            return []

        output = []
        for i, emb_id in enumerate(results["ids"][0]):
            meta = dict(results["metadatas"][0][i]) if results.get("metadatas") else {}
            distance = results["distances"][0][i] if results.get("distances") else 0.0
            score = round(1.0 - distance, 6)
            emb = results.get("embeddings")
            vector = emb[0][i].tolist() if emb and emb[0] else None
            output.append({
                "embedding_id": emb_id,
                "chunk_id": meta.pop("chunk_id", None),
                "knowledge_id": meta.pop("knowledge_id", None),
                "score": score,
                "metadata": {k: v for k, v in meta.items() if k not in ("chunk_id", "knowledge_id")},
                "vector": vector,
            })
        return output

    async def delete(self, embedding_id: str) -> bool:
        try:
            self._collection.delete(ids=[embedding_id])
            return True
        except Exception:
            return False

    async def delete_by_filter(self, filters: dict) -> int:
        try:
            where = self._convert_filters(filters)
            count_before = self._collection.count()
            self._collection.delete(where=where)
            return count_before - self._collection.count()
        except Exception:
            return 0

    async def count(self) -> int:
        try:
            return self._collection.count()
        except Exception:
            return 0

    async def clear(self) -> None:
        try:
            existing = self._collection.get()
            if existing["ids"]:
                self._collection.delete(ids=existing["ids"])
        except Exception:
            pass

    def provider_name(self) -> str:
        return "chroma"

    def _convert_filters(self, filters: dict) -> dict | None:
        if not filters:
            return None
        result: dict[str, Any] = {}
        for key, value in filters.items():
            if key in ("$and", "$or"):
                result[key] = [self._convert_filters(cond) if isinstance(cond, dict) else cond for cond in value]
            elif isinstance(value, dict):
                result[key] = value
            else:
                result[key] = value
        return result if result else None
