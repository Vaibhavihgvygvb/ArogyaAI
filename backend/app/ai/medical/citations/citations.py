from typing import Any

from app.ai.medical.interfaces.interfaces import CitationEngineABC
from app.ai.medical.schemas.schemas import CitationEntry


class CitationEngine(CitationEngineABC):
    async def build_citations(self, results: list[Any], top_k: int = 10) -> list[CitationEntry]:
        entries: list[CitationEntry] = []
        for result in results[:top_k]:
            metadata = {}
            if hasattr(result, "metadata") and result.metadata:
                metadata = result.metadata
                if isinstance(metadata, dict):
                    metadata = metadata
                elif hasattr(metadata, "model_dump"):
                    metadata = metadata.model_dump()

            source = None
            if isinstance(metadata, dict):
                source = metadata.get("source_document", metadata.get("source", metadata.get("filename")))

            evidence_text = ""
            if hasattr(result, "content") and result.content:
                evidence_text = result.content
            elif hasattr(result, "evidence_text") and result.evidence_text:
                evidence_text = result.evidence_text

            knowledge_id = ""
            if hasattr(result, "knowledge_id") and result.knowledge_id:
                knowledge_id = result.knowledge_id

            chunk_id = ""
            if hasattr(result, "chunk_id") and result.chunk_id:
                chunk_id = result.chunk_id

            document_id = ""
            if hasattr(result, "document_id") and result.document_id:
                document_id = result.document_id

            relevance_score = 0.0
            if hasattr(result, "score") and result.score is not None:
                relevance_score = float(result.score)

            entry = CitationEntry(
                chunk_id=chunk_id,
                knowledge_id=knowledge_id,
                document_id=document_id or knowledge_id,
                source=str(source) if source else None,
                relevance_score=relevance_score,
                evidence_text=evidence_text,
                metadata=metadata if isinstance(metadata, dict) else {},
            )
            entries.append(entry)
        return entries
