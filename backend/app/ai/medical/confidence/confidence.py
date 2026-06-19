from app.ai.medical.interfaces.interfaces import ConfidenceEngineABC
from app.ai.medical.schemas.schemas import CitationEntry, ConfidenceScore, IntentType, MedicalIntent


class ConfidenceEngine(ConfidenceEngineABC):
    async def score(
        self,
        query: str,
        response: str,
        citations: list[CitationEntry],
        intent: MedicalIntent,
    ) -> ConfidenceScore:
        retrieval_confidence = self._score_retrieval(citations, intent)
        evidence_confidence = self._score_evidence(citations)
        generation_confidence = self._score_generation(response, citations)
        citation_coverage = self._score_citation_coverage(citations)

        overall = (
            retrieval_confidence * 0.25
            + evidence_confidence * 0.25
            + generation_confidence * 0.30
            + citation_coverage * 0.20
        )

        return ConfidenceScore(
            overall=round(overall, 4),
            retrieval_confidence=round(retrieval_confidence, 4),
            evidence_confidence=round(evidence_confidence, 4),
            generation_confidence=round(generation_confidence, 4),
            citation_coverage=round(citation_coverage, 4),
        )

    def _score_retrieval(self, citations: list[CitationEntry], intent: MedicalIntent) -> float:
        if not citations:
            return 0.0
        avg_relevance = sum(c.relevance_score for c in citations) / len(citations)
        num_factor = min(len(citations) / 5, 1.0)
        return min(avg_relevance * 0.6 + num_factor * 0.4, 1.0)

    def _score_evidence(self, citations: list[CitationEntry]) -> float:
        if not citations:
            return 0.0
        with_content = sum(1 for c in citations if c.evidence_text and len(c.evidence_text.strip()) > 50)
        coverage = with_content / len(citations)
        has_sources = sum(1 for c in citations if c.source or c.document_id)
        source_factor = has_sources / len(citations)
        return min(coverage * 0.6 + source_factor * 0.4, 1.0)

    def _score_generation(self, response: str, citations: list[CitationEntry]) -> float:
        if not response or not response.strip():
            return 0.0
        words = len(response.split())
        length_factor = min(words / 100, 1.0)
        uncertainty_terms = [
            "may", "might", "could", "possibly", "potentially", "unclear",
            "unknown", "not well understood", "limited evidence", "further research",
        ]
        uncertainty_count = sum(1 for t in uncertainty_terms if t in response.lower())
        certainty_factor = max(1.0 - (uncertainty_count * 0.1), 0.3)

        citation_references = 0
        for c in citations:
            if c.chunk_id and c.chunk_id in response:
                citation_references += 1
        citation_ref_factor = min(citation_references / max(len(citations), 1) * 1.5, 1.0)

        return min(length_factor * 0.3 + certainty_factor * 0.4 + citation_ref_factor * 0.3, 1.0)

    def _score_citation_coverage(self, citations: list[CitationEntry]) -> float:
        if not citations:
            return 0.0
        unique_knowledge = len(set(c.knowledge_id for c in citations if c.knowledge_id))
        knowledge_factor = min(unique_knowledge / 3, 1.0)
        total_factor = min(len(citations) / 5, 1.0)
        return min(knowledge_factor * 0.6 + total_factor * 0.4, 1.0)
