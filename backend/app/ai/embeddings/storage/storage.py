import json
import os
from datetime import datetime, timezone
from typing import Any

from app.ai.embeddings.exceptions.exceptions import StorageError
from app.ai.embeddings.interfaces.interfaces import EmbeddingStorage
from app.ai.embeddings.schemas.schemas import (
    EmbeddingRecord,
    EmbeddingStatus,
    EmbeddingVector,
)
from app.ai.embeddings.utils.utils import generate_embedding_id


class LocalEmbeddingStorage(EmbeddingStorage):
    def __init__(self, base_path: str):
        self._base_path = base_path
        self._records_path = os.path.join(base_path, "records")
        self._vectors_path = os.path.join(base_path, "vectors")
        os.makedirs(self._records_path, exist_ok=True)
        os.makedirs(self._vectors_path, exist_ok=True)

    def _record_path(self, embedding_id: str) -> str:
        return os.path.join(self._records_path, f"{embedding_id}.json")

    def _vector_path(self, embedding_id: str) -> str:
        return os.path.join(self._vectors_path, f"{embedding_id}.json")

    async def store_vector(self, vector: EmbeddingVector) -> str:
        path = self._vector_path(vector.id)
        data = vector.model_dump(mode="json")
        data["created_at"] = vector.created_at.isoformat()
        data["updated_at"] = vector.updated_at.isoformat()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise StorageError(f"Failed to store vector {vector.id}: {e}")
        return path

    async def store_record(self, record: EmbeddingRecord) -> str:
        path = self._record_path(record.id)
        data = record.model_dump(mode="json")
        data["created_at"] = record.created_at.isoformat()
        data["updated_at"] = record.updated_at.isoformat()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise StorageError(f"Failed to store record {record.id}: {e}")
        return path

    async def get_vector(self, embedding_id: str) -> EmbeddingVector | None:
        path = self._vector_path(embedding_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return EmbeddingVector(**data)
        except (OSError, KeyError, ValueError) as e:
            raise StorageError(f"Failed to retrieve vector {embedding_id}: {e}")

    async def get_record(self, embedding_id: str) -> EmbeddingRecord | None:
        path = self._record_path(embedding_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return EmbeddingRecord(**data)
        except (OSError, KeyError, ValueError) as e:
            raise StorageError(f"Failed to retrieve record {embedding_id}: {e}")

    async def delete(self, embedding_id: str) -> bool:
        r_path = self._record_path(embedding_id)
        v_path = self._vector_path(embedding_id)
        deleted = False
        for path in [r_path, v_path]:
            if os.path.exists(path):
                try:
                    os.remove(path)
                    deleted = True
                except OSError as e:
                    raise StorageError(f"Failed to delete embedding {embedding_id}: {e}")
        return deleted

    async def list_records(
        self,
        knowledge_id: str | None = None,
        chunk_id: str | None = None,
        status: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[EmbeddingRecord], int]:
        try:
            files = os.listdir(self._records_path)
        except OSError as e:
            raise StorageError(f"Failed to list records: {e}")

        records: list[EmbeddingRecord] = []
        for fname in files:
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(self._records_path, fname), "r", encoding="utf-8") as f:
                    data = json.load(f)
                record = EmbeddingRecord(**data)
                if knowledge_id and record.knowledge_id != knowledge_id:
                    continue
                if chunk_id and record.chunk_id != chunk_id:
                    continue
                if status and record.status.value != status:
                    continue
                records.append(record)
            except (OSError, ValueError):
                continue

        total = len(records)
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[offset : offset + limit], total

    async def exists(self, embedding_id: str) -> bool:
        return os.path.exists(self._record_path(embedding_id))
