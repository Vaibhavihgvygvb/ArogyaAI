from app.ai.medical.engine.schemas import QueryUnderstandingResult
from app.ai.medical.reasoning.exceptions.exceptions import ContextRankingError
from app.ai.medical.reasoning.interfaces.interfaces import (
    RETRIEVAL_RESULT_TYPE,
    ContextRankerABC,
)
from app.ai.medical.reasoning.schemas.schemas import (
    RankedContext,
    RetrievalPlan,
)


class ContextRanker(ContextRankerABC):
    async def rank(
        self,
        results: list[RETRIEVAL_RESULT_TYPE],
        query: str,
        retrieval_plan: RetrievalPlan,
        analysis: QueryUnderstandingResult,
    ) -> RankedContext:
        if not results:
            return RankedContext(
                chunk_ids=[],
                ranking_scores=[],
                diversity_scores=[],
                total_original=0,
                retained=0,
            )

        scored = self._score_results(results, query, retrieval_plan, analysis)
        diversity_scores = self._compute_diversity_scores(scored)
        deduped = self._deduplicate_and_filter(scored, diversity_scores)

        chunk_ids = [item["id"] for item in deduped]
        scores = [item["score"] for item in deduped]
        div_scores = [item["diversity"] for item in deduped]

        return RankedContext(
            chunk_ids=chunk_ids,
            ranking_scores=scores,
            diversity_scores=div_scores,
            total_original=len(results),
            retained=len(chunk_ids),
        )

    def _score_results(
        self,
        results: list[RETRIEVAL_RESULT_TYPE],
        query: str,
        retrieval_plan: RetrievalPlan,
        analysis: QueryUnderstandingResult,
    ) -> list[dict]:
        scored = []
        query_lower = query.lower()

        for r in results:
            base_score = getattr(r, "score", 0) or 0
            content = getattr(r, "content", "") or getattr(r, "evidence_text", "") or ""
            chunk_id = getattr(r, "chunk_id", "") or str(id(r))
            knowledge_id = getattr(r, "knowledge_id", "") or ""

            keyword_boost = 0.0
            content_lower = content.lower()
            if query_lower in content_lower:
                keyword_boost = 0.05
            query_terms = query_lower.split()
            matches = sum(1 for t in query_terms if t in content_lower)
            if matches > 0:
                keyword_boost = min(keyword_boost + 0.02 * matches, 0.2)

            freshness = 0.0
            meta = getattr(r, "metadata", {}) or {}
            if analysis.urgency and analysis.urgency.level in ("emergency", "urgent"):
                if "recency" in meta:
                    try:
                        freshness = float(meta.get("recency", 0)) * 0.1
                    except (ValueError, TypeError):
                        pass

            final_score = base_score + keyword_boost + freshness

            scored.append({
                "id": chunk_id,
                "knowledge_id": knowledge_id,
                "content": content,
                "score": round(final_score, 4),
                "diversity": 0.0,
                "metadata": meta,
                "original_score": base_score,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)

        if retrieval_plan.weights:
            for i, s in enumerate(scored):
                if i < len(retrieval_plan.weights):
                    s["score"] *= retrieval_plan.weights[i]

        return scored

    def _compute_diversity_scores(self, scored: list[dict]) -> list[float]:
        if not scored:
            return []

        diversity = [1.0] * len(scored)
        for i in range(len(scored)):
            for j in range(i):
                overlap = self._jaccard_similarity(scored[i]["content"], scored[j]["content"])
                if overlap > 0.7:
                    diversity[i] *= (1 - overlap)
        return [round(d, 4) for d in diversity]

    def _deduplicate_and_filter(
        self,
        scored: list[dict],
        diversity_scores: list[float],
    ) -> list[dict]:
        seen_knowledge_ids: set[str] = set()
        deduped: list[dict] = []

        for i, item in enumerate(scored):
            kid = item.get("knowledge_id", "")
            if kid and kid in seen_knowledge_ids:
                continue
            if kid:
                seen_knowledge_ids.add(kid)

            item["diversity"] = diversity_scores[i] if i < len(diversity_scores) else 1.0
            combined = item["score"] * item["diversity"]
            item["combined_score"] = round(combined, 4)
            deduped.append(item)

        deduped.sort(key=lambda x: x["combined_score"], reverse=True)
        return deduped

    def _jaccard_similarity(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)
