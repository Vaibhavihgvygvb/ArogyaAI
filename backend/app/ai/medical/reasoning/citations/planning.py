from app.ai.medical.reasoning.exceptions.exceptions import CitationPlanningError
from app.ai.medical.reasoning.interfaces.interfaces import (
    RETRIEVAL_RESULT_TYPE,
    CitationPlannerABC,
)
from app.ai.medical.reasoning.schemas.schemas import CitationPlan, RankedContext


class CitationPlanner(CitationPlannerABC):
    async def plan(
        self,
        results: list[RETRIEVAL_RESULT_TYPE],
        ranked_context: RankedContext,
    ) -> CitationPlan:
        if not results:
            return CitationPlan(
                chunk_ids=[],
                citation_map={},
                coverage=0.0,
                priority_order=[],
            )

        chunk_map = self._build_chunk_map(results)
        chunk_ids = list(ranked_context.chunk_ids) if ranked_context.chunk_ids else list(chunk_map.keys())
        citation_map = self._build_citation_map(chunk_map, chunk_ids)

        covered = sum(1 for cids in citation_map.values() if cids)
        coverage = covered / len(citation_map) if citation_map else 0.0

        priority_order = self._prioritize(chunk_ids, chunk_map, ranked_context)

        return CitationPlan(
            chunk_ids=chunk_ids,
            citation_map=citation_map,
            coverage=round(coverage, 4),
            priority_order=priority_order,
        )

    def _build_chunk_map(self, results: list[RETRIEVAL_RESULT_TYPE]) -> dict[str, dict]:
        chunk_map: dict[str, dict] = {}
        for r in results:
            chunk_id = getattr(r, "chunk_id", "") or str(id(r))
            knowledge_id = getattr(r, "knowledge_id", "") or ""
            content = getattr(r, "content", "") or getattr(r, "evidence_text", "") or ""
            score = getattr(r, "score", 0) or 0
            chunk_map[chunk_id] = {
                "id": chunk_id,
                "knowledge_id": knowledge_id,
                "content": content,
                "score": score,
            }
        return chunk_map

    def _build_citation_map(
        self,
        chunk_map: dict[str, dict],
        chunk_ids: list[str],
    ) -> dict[str, list[str]]:
        citation_map: dict[str, list[str]] = {}
        for i, cid in enumerate(chunk_ids):
            chunk = chunk_map.get(cid)
            if not chunk:
                citation_map[cid] = []
                continue
            refs = []
            content_lower = chunk["content"].lower()
            if hasattr(chunk, "metadata"):
                meta = chunk.get("metadata", {})
                if meta and isinstance(meta, dict):
                    for key in ("source", "document_id", "title"):
                        val = meta.get(key)
                        if val:
                            refs.append(str(val))
            source_num = i + 1
            refs.append(f"[Source {source_num}]")
            citation_map[cid] = refs
        return citation_map

    def _prioritize(
        self,
        chunk_ids: list[str],
        chunk_map: dict[str, dict],
        ranked_context: RankedContext,
    ) -> list[str]:
        scored = []
        for cid in chunk_ids:
            chunk = chunk_map.get(cid, {})
            score = chunk.get("score", 0) or 0
            content = chunk.get("content", "") or ""
            length_bonus = min(len(content) / 1000, 0.1)
            scored.append((cid, score + length_bonus))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in scored]
