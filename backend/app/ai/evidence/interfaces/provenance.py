from abc import ABC, abstractmethod

from app.ai.evidence.schemas import EvidenceState, ProvenanceEntry


class ProvenanceTracker(ABC):
    @abstractmethod
    async def track(
        self, entry: ProvenanceEntry, state: EvidenceState | None = None
    ) -> list[ProvenanceEntry]:
        ...

    @abstractmethod
    async def get_graph(
        self, entries: list[ProvenanceEntry]
    ) -> dict:
        ...
