from app.ai.medical.exceptions.exceptions import ResponseBuilderError
from app.ai.medical.interfaces.interfaces import ResponseBuilderABC
from app.ai.medical.schemas.schemas import (
    CitationEntry,
    ConfidenceScore,
    MedicalIntent,
    MedicalMetadata,
    MedicalReasoning,
    MedicalResponse,
    SafetyCheckResult,
)


class ResponseBuilder(ResponseBuilderABC):
    async def build(
        self,
        answer: str,
        intent: MedicalIntent | None = None,
        reasoning: MedicalReasoning | None = None,
        citations: list[CitationEntry] | None = None,
        confidence: ConfidenceScore | None = None,
        safety: SafetyCheckResult | None = None,
        metadata: MedicalMetadata | None = None,
        conversation_id: str | None = None,
    ) -> MedicalResponse:
        if not answer or not answer.strip():
            raise ResponseBuilderError("Response answer cannot be empty")

        citations_list = citations or []

        final_answer = answer
        if citations_list:
            citation_refs = self._format_citation_references(citations_list)
            final_answer = f"{answer}\n\n{citation_refs}"

        if safety and not safety.passed:
            safety_warning = (
                "\n\n**Note**: This response was flagged by safety validation. "
                "Please verify all information with a qualified healthcare professional."
            )
            if safety_warning not in final_answer:
                final_answer += safety_warning

        return MedicalResponse(
            answer=final_answer,
            intent=intent,
            reasoning=reasoning,
            citations=citations_list,
            confidence=confidence,
            safety=safety,
            metadata=metadata,
            conversation_id=conversation_id,
        )

    def _format_citation_references(self, citations: list[CitationEntry]) -> str:
        lines = ["---", "**References:**"]
        seen_sources: set[str] = set()
        ref_num = 1

        for c in citations:
            source_key = c.source or c.knowledge_id or c.chunk_id
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)

            source_name = c.source or f"Document {c.knowledge_id}"
            ref_line = f"[{ref_num}] {source_name}"
            if c.relevance_score > 0:
                ref_line += f" (relevance: {c.relevance_score:.2f})"
            lines.append(ref_line)
            ref_num += 1

        return "\n".join(lines)
