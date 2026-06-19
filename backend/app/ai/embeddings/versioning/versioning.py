from datetime import datetime, timezone

from app.ai.embeddings.exceptions.exceptions import VersionMismatchError
from app.ai.embeddings.interfaces.interfaces import EmbeddingVersionManager
from app.ai.embeddings.schemas.schemas import EmbeddingVersion


class InMemoryVersionManager(EmbeddingVersionManager):
    def __init__(self):
        self._versions: dict[str, list[EmbeddingVersion]] = {}
        self._active: dict[str, int] = {}
        self._knowledge_links: dict[str, str] = {}

    def _key(self, provider: str, model: str) -> str:
        return f"{provider}:{model}"

    async def create_version(
        self, provider: str, model: str, dimension: int, checksum: str, count: int,
        knowledge_version: str = "",
    ) -> int:
        key = self._key(provider, model)
        if key not in self._versions:
            self._versions[key] = []
        version_num = len(self._versions[key]) + 1
        for v in self._versions[key]:
            v.is_active = False
        version = EmbeddingVersion(
            version=version_num,
            provider=provider,
            model=model,
            dimension=dimension,
            checksum=checksum,
            count=count,
            knowledge_version=knowledge_version,
            created_at=datetime.now(timezone.utc),
            is_active=True,
        )
        self._versions[key].append(version)
        self._active[key] = version_num
        if knowledge_version:
            self._knowledge_links[key] = knowledge_version
        return version_num

    async def get_active_version(self, provider: str, model: str) -> int | None:
        key = self._key(provider, model)
        return self._active.get(key)

    async def deprecate_version(self, provider: str, model: str, version: int) -> None:
        key = self._key(provider, model)
        if key in self._versions:
            for v in self._versions[key]:
                if v.version == version:
                    v.is_active = False
            if self._active.get(key) == version:
                del self._active[key]

    async def get_versions(self, provider: str, model: str) -> list[int]:
        key = self._key(provider, model)
        if key not in self._versions:
            return []
        return [v.version for v in self._versions[key]]

    async def get_version_info(self, provider: str, model: str, version: int) -> EmbeddingVersion | None:
        key = self._key(provider, model)
        if key not in self._versions:
            return None
        for v in self._versions[key]:
            if v.version == version:
                return v
        return None

    async def rollback(self, provider: str, model: str, target_version: int) -> int | None:
        key = self._key(provider, model)
        if key not in self._versions:
            return None
        versions = self._versions[key]
        target = None
        for v in versions:
            if v.version == target_version:
                target = v
                break
        if target is None:
            raise VersionMismatchError(f"Version {target_version} not found for {provider}/{model}")
        target.is_active = True
        for v in versions:
            if v.version > target_version:
                v.is_active = False
        self._active[key] = target_version
        return target_version
