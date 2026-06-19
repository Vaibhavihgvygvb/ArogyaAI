from collections import defaultdict

from app.ai.evidence.interfaces.citation import CitationFormatter, CitationGenerator
from app.ai.evidence.schemas import (
    Citation,
    CitationGroup,
    CitationStyle,
    EvidenceState,
    FormattedCitation,
    VerificationResult,
)


class CitationGeneratorEngine(CitationGenerator):
    async def generate(
        self,
        verification_results: list[VerificationResult],
        state: EvidenceState | None = None,
    ) -> list[Citation]:
        if not verification_results:
            return []

        citations = []
        for i, vr in enumerate(verification_results):
            for j, source in enumerate(vr.supporting_sources):
                citations.append(
                    Citation(
                        citation_id=f"cit_{i}_{j}",
                        span_index=i,
                        evidence_text=vr.span.claim,
                        source=source,
                        citation_number=0,
                        inline_ref=f"({source.authority_score:.0%} confidence)",
                        confidence=vr.confidence,
                    )
                )
        return citations

    async def group_by_claim(
        self, citations: list[Citation]
    ) -> list[CitationGroup]:
        groups = defaultdict(list)
        for c in citations:
            groups[c.evidence_text].append(c)
        return [
            CitationGroup(
                claim=claim, citations=group, total_citations=len(group)
            )
            for claim, group in groups.items()
        ]


class CitationFormatterEngine(CitationFormatter):
    async def format(
        self,
        citations: list[Citation],
        style: CitationStyle = CitationStyle.AMA,
    ) -> FormattedCitation:
        if not citations:
            return FormattedCitation(style=style, text="", markdown="")

        refs = []
        for i, c in enumerate(citations, start=1):
            refs.append(self._format_single(c, style, i))
            c.citation_number = i

        text = "\n".join(
            f"[{c.citation_number}] {c.evidence_text}" for c in citations
        )
        markdown = self._build_markdown(citations, refs)

        return FormattedCitation(
            style=style,
            text=text,
            markdown=markdown,
            citations=citations,
            reference_list=refs,
        )

    async def supported_styles(self) -> list[CitationStyle]:
        return list(CitationStyle)

    def _format_single(
        self, citation: Citation, style: CitationStyle, number: int
    ) -> str:
        s = citation.source
        authors = ", ".join(s.authors) if s.authors else "Unknown"
        title = s.title or "Untitled"
        if style == CitationStyle.AMA:
            return f"{number}. {authors}. {title}. {s.journal or 'Unknown Journal'}. {s.publication_date or 'n.d'}."
        elif style == CitationStyle.APA:
            year = s.publication_date[:4] if s.publication_date else "n.d."
            return f"{authors} ({year}). {title}. {s.journal or 'Unknown Journal'}."
        elif style == CitationStyle.VANCOUVER:
            return f"{number}. {authors}. {title}. {s.journal or 'Unknown Journal'}. {s.publication_date or 'n.d'}."
        elif style == CitationStyle.IEEE:
            return f"[{number}] {authors}, \"{title},\" {s.journal or 'Unknown Journal'}, {s.publication_date or 'n.d'}."
        elif style == CitationStyle.MLA:
            return f"{authors}. \"{title}.\" {s.journal or 'Unknown Journal'}, {s.publication_date or 'n.d'}."
        elif style == CitationStyle.CHICAGO:
            return f"{authors}. \"{title}.\" {s.journal or 'Unknown Journal'} ({s.publication_date or 'n.d'})."
        return f"{number}. {authors}. {title}."

    def _build_markdown(
        self, citations: list[Citation], refs: list[str]
    ) -> str:
        lines = ["## References\n"]
        for i, (c, ref) in enumerate(zip(citations, refs), start=1):
            lines.append(f"[^{i}]: {ref}")
            lines.append("")
        return "\n".join(lines)
