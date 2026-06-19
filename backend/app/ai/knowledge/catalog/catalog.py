import json
import os
from datetime import datetime, timezone

from app.ai.knowledge.exceptions.exceptions import CatalogError
from app.ai.knowledge.schemas.schemas import CatalogEntry, DocumentMetadata, DocumentStatus


class KnowledgeCatalog:
    def __init__(self, catalog_path: str):
        self._catalog_path = catalog_path
        self._entries: dict[str, CatalogEntry] = {}
        os.makedirs(os.path.dirname(self._catalog_path), exist_ok=True)
        self._load()

    def _load(self) -> None:
        if os.path.exists(self._catalog_path):
            try:
                with open(self._catalog_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    entry = CatalogEntry(**item)
                    self._entries[entry.id] = entry
            except (OSError, json.JSONDecodeError) as e:
                raise CatalogError(f"Failed to load catalog: {e}")

    def _save(self) -> None:
        try:
            data = [entry.model_dump(mode="json") for entry in self._entries.values()]
            with open(self._catalog_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
        except OSError as e:
            raise CatalogError(f"Failed to save catalog: {e}")

    def add_entry(
        self,
        entry: CatalogEntry,
    ) -> CatalogEntry:
        self._entries[entry.id] = entry
        self._save()
        return entry

    def update_entry(
        self,
        document_id: str,
        status: DocumentStatus | None = None,
        version: int | None = None,
        metadata: DocumentMetadata | None = None,
    ) -> CatalogEntry | None:
        entry = self._entries.get(document_id)
        if entry is None:
            return None
        updated = entry.model_copy(deep=True)
        if status is not None:
            updated.status = status
        if version is not None:
            updated.version = version
        if metadata is not None:
            updated.metadata = metadata
        updated.updated_at = datetime.now(timezone.utc)
        self._entries[document_id] = updated
        self._save()
        return updated

    def get_entry(self, document_id: str) -> CatalogEntry | None:
        return self._entries.get(document_id)

    def list_entries(
        self,
        status: DocumentStatus | None = None,
        format: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[CatalogEntry]:
        entries = list(self._entries.values())
        if status is not None:
            entries = [e for e in entries if e.status == status]
        if format is not None:
            entries = [e for e in entries if e.format == format]
        entries.sort(key=lambda e: e.created_at, reverse=True)
        return entries[offset : offset + limit]

    def remove_entry(self, document_id: str) -> bool:
        if document_id in self._entries:
            del self._entries[document_id]
            self._save()
            return True
        return False

    def count_entries(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()
        self._save()
