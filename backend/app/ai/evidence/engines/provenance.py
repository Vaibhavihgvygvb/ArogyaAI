from datetime import datetime

from app.ai.evidence.interfaces.provenance import ProvenanceTracker
from app.ai.evidence.schemas import EvidenceState, ProvenanceAction, ProvenanceEntry


class ProvenanceTrackerEngine(ProvenanceTracker):
    async def track(
        self, entry: ProvenanceEntry, state: EvidenceState | None = None
    ) -> list[ProvenanceEntry]:
        if state is not None:
            state.provenance.append(entry)
        return [entry]

    async def get_graph(self, entries: list[ProvenanceEntry]) -> dict:
        if not entries:
            return {"entries": [], "total_time_ms": 0.0, "engine_count": 0}

        total_time = sum(e.processing_time_ms for e in entries)
        return {
            "entries": [
                {
                    "action": e.action.value,
                    "engine": e.engine_name,
                    "time_ms": e.processing_time_ms,
                    "confidence": e.confidence,
                    "timestamp": e.timestamp.isoformat() if e.timestamp else None,
                }
                for e in entries
            ],
            "total_time_ms": round(total_time, 2),
            "engine_count": len(entries),
        }
