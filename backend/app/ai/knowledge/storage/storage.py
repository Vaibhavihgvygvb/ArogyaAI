import json
import os
from datetime import datetime

from app.ai.knowledge.exceptions.exceptions import StorageError
from app.ai.knowledge.interfaces.interfaces import StorageProvider
from app.ai.knowledge.schemas.schemas import DocumentChunk, DocumentMetadata, DocumentStatus, KnowledgeDocument


class LocalFileStorage(StorageProvider):
    def __init__(self, base_path: str):
        self._base_path = base_path
        os.makedirs(self._base_path, exist_ok=True)

    def _document_path(self, document_id: str) -> str:
        return os.path.join(self._base_path, f"{document_id}.json")

    async def store(self, document: KnowledgeDocument) -> str:
        path = self._document_path(document.id)
        data = document.model_dump(mode="json")
        data["created_at"] = document.created_at.isoformat()
        data["updated_at"] = document.updated_at.isoformat()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except OSError as e:
            raise StorageError(f"Failed to store document {document.id}: {e}")
        return path

    async def retrieve(self, document_id: str) -> KnowledgeDocument | None:
        path = self._document_path(document_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            metadata = DocumentMetadata(**data.get("metadata", {}))
            chunks = [DocumentChunk(**c) for c in data.get("chunks", [])]
            return KnowledgeDocument(
                id=data["id"],
                filename=data["filename"],
                format=data["format"],
                size_bytes=data["size_bytes"],
                checksum=data["checksum"],
                status=DocumentStatus(data["status"]),
                version=data.get("version", 1),
                metadata=metadata,
                chunks=chunks,
                error=data.get("error"),
                created_at=datetime.fromisoformat(data["created_at"]),
                updated_at=datetime.fromisoformat(data["updated_at"]),
            )
        except (OSError, KeyError, ValueError) as e:
            raise StorageError(f"Failed to retrieve document {document_id}: {e}")

    async def delete(self, document_id: str) -> bool:
        path = self._document_path(document_id)
        if not os.path.exists(path):
            return False
        try:
            os.remove(path)
            return True
        except OSError as e:
            raise StorageError(f"Failed to delete document {document_id}: {e}")

    async def list_documents(self) -> list[str]:
        try:
            files = os.listdir(self._base_path)
            return [f.replace(".json", "") for f in files if f.endswith(".json")]
        except OSError as e:
            raise StorageError(f"Failed to list documents: {e}")

    async def document_exists(self, document_id: str) -> bool:
        return os.path.exists(self._document_path(document_id))
