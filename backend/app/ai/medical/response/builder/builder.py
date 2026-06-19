import re

from app.ai.medical.response.config.config import ResponseSettings
from app.ai.medical.response.exceptions.exceptions import StructuredResponseError
from app.ai.medical.response.interfaces.interfaces import StructuredResponseBuilderABC
from app.ai.medical.response.schemas.schemas import (
    Citation,
    ClinicalSection,
    ClinicalSectionType,
    GenerateResponse,
    ResponseMetadata,
    StructuredAnswer,
)
from app.ai.medical.reasoning.schemas.schemas import ReasoningPlan

_SECTION_HEADER_PATTERN = re.compile(
    r"^#{1,3}\s+(.+)$",
    re.MULTILINE,
)

_ASTERISK_SECTION_PATTERN = re.compile(
    r"^\*\*(.+?)\*\*$",
    re.MULTILINE,
)

_TYPE_KEYWORDS: dict[ClinicalSectionType, list[str]] = {
    ClinicalSectionType.SUMMARY: ["summary", "overview", "key points"],
    ClinicalSectionType.SYMPTOM_ANALYSIS: ["symptom", "clinical presentation", "manifestation"],
    ClinicalSectionType.DIFFERENTIAL_DIAGNOSIS: ["differential diagnosis", "considerations", "possible causes"],
    ClinicalSectionType.DIAGNOSTIC_APPROACH: ["diagnostic", "test", "evaluation", "assessment"],
    ClinicalSectionType.TREATMENT_OPTIONS: ["treatment", "therapy", "management", "option"],
    ClinicalSectionType.MEDICATION_INFO: ["medication", "drug", "pharmaco", "dosing", "dosage"],
    ClinicalSectionType.RISK_FACTORS: ["risk factor", "complication", "predispo"],
    ClinicalSectionType.PREVENTION: ["prevention", "preventive", "screening", "prophylaxis"],
    ClinicalSectionType.PROGNOSIS: ["prognosis", "outcome", "survival", "recovery"],
    ClinicalSectionType.FOLLOW_UP: ["follow[- ]up", "monitor", "surveillance"],
    ClinicalSectionType.LIFESTYLE: ["lifestyle", "diet", "exercise", "nutrition", "activity"],
    ClinicalSectionType.MONITORING: ["monitoring", "track", "HbA1c", "blood pressure"],
    ClinicalSectionType.COMPLICATIONS: ["complication", "adverse", "side effect"],
    ClinicalSectionType.REFERRAL: ["referral", "specialist", "consult"],
    ClinicalSectionType.PATIENT_EDUCATION: ["patient education", "self-care", "when to seek"],
    ClinicalSectionType.EMERGENCY_GUIDANCE: ["emergency", "urgent", "immediately", "call 911", "call emergency"],
    ClinicalSectionType.GENERAL_INFO: ["information", "background", "context"],
}


class StructuredResponseBuilder(StructuredResponseBuilderABC):
    def __init__(self, settings: ResponseSettings | None = None):
        self._settings = settings or ResponseSettings()

    async def build(
        self,
        raw_content: str,
        reasoning_plan: ReasoningPlan | None = None,
        query: str = "",
        conversation_id: str | None = None,
    ) -> GenerateResponse:
        if not raw_content or not raw_content.strip():
            raise StructuredResponseError("Raw content cannot be empty")

        sections = self._parse_sections(raw_content)
        key_findings = self._extract_key_findings(sections, raw_content)
        limitations = self._extract_limitations(raw_content)
        citations = self._extract_citations(raw_content)
        disclaimer = self._build_disclaimer(reasoning_plan)

        structured_answer = StructuredAnswer(
            summary=self._extract_summary(sections, raw_content),
            sections=sections,
            key_findings=key_findings,
            limitations=limitations,
            disclaimer=disclaimer,
            formatted_text=self._format_text(raw_content, sections),
        )

        return GenerateResponse(
            query=query,
            answer=self._format_final_answer(raw_content, citations, disclaimer),
            structured_answer=structured_answer,
            sections=sections,
            citations=citations,
            key_findings=key_findings,
            limitations=limitations,
            disclaimer=disclaimer,
            conversation_id=conversation_id,
        )

    def _parse_sections(self, content: str) -> list[ClinicalSection]:
        sections: list[ClinicalSection] = []
        lines = content.split("\n")
        current_header = ""
        current_content: list[str] = []
        current_section_type = ClinicalSectionType.GENERAL_INFO
        priority_counter = 0

        for line in lines:
            header_match = _SECTION_HEADER_PATTERN.match(line)
            asterisk_match = _ASTERISK_SECTION_PATTERN.match(line)

            if header_match or asterisk_match:
                if current_header and current_content:
                    section = self._build_section(current_header, current_content, current_section_type, priority_counter)
                    if section:
                        sections.append(section)
                    priority_counter += 1

                current_header = (header_match or asterisk_match).group(1).strip()
                current_content = []
                current_section_type = self._classify_section(current_header)
            else:
                current_content.append(line)

        if current_header and current_content:
            section = self._build_section(current_header, current_content, current_section_type, priority_counter)
            if section:
                sections.append(section)

        if not sections:
            sections.append(
                ClinicalSection(
                    section_type=ClinicalSectionType.SUMMARY,
                    title="Summary",
                    content=content[:2000] if len(content) > 2000 else content,
                    priority=0,
                )
            )

        return sections[: self._settings.RESPONSE_MAX_SECTIONS]

    def _build_section(
        self,
        header: str,
        content_lines: list[str],
        section_type: ClinicalSectionType,
        priority: int,
    ) -> ClinicalSection | None:
        content = "\n".join(content_lines).strip()
        if not content:
            return None
        return ClinicalSection(
            section_type=section_type,
            title=header,
            content=content,
            priority=priority,
        )

    def _classify_section(self, header: str) -> ClinicalSectionType:
        header_lower = header.lower()
        best_type = ClinicalSectionType.GENERAL_INFO
        best_score = 0

        for section_type, keywords in _TYPE_KEYWORDS.items():
            for keyword in keywords:
                if re.search(keyword, header_lower):
                    score = len(keyword)
                    if score > best_score:
                        best_score = score
                        best_type = section_type

        return best_type

    def _extract_key_findings(self, sections: list[ClinicalSection], content: str) -> list[str]:
        findings: list[str] = []

        for section in sections:
            for line in section.content.split("\n"):
                stripped = line.strip()
                if stripped.startswith("- **") or stripped.startswith("* **"):
                    finding = stripped.lstrip("- *").strip()
                    if finding.endswith("**"):
                        finding = finding[:-2]
                    if len(finding) > 10 and finding not in findings:
                        findings.append(finding)

        if not findings:
            bullet_pattern = re.findall(r"^[-*+]\s+(.+)$", content, re.MULTILINE)
            for b in bullet_pattern[:5]:
                if len(b) > 15 and b not in findings:
                    findings.append(b)

        return findings[:10]

    def _extract_limitations(self, content: str) -> list[str]:
        limitations: list[str] = []
        content_lower = content.lower()

        limitation_patterns = [
            r"limitation[^.]*",
            r"this (?:information|response) (?:is|does|may)[^.]*",
            r"further research[^.]*",
            r"limited evidence[^.]*",
            r"not a substitute[^.]*",
            r"consult (?:a|your) (?:healthcare|doctor|physician)[^.]*",
        ]

        for pattern in limitation_patterns:
            matches = re.findall(pattern, content_lower)
            for m in matches[:2]:
                clean = m.strip()
                if clean not in limitations:
                    limitations.append(clean.capitalize())

        return limitations[:3]

    def _extract_citations(self, content: str) -> list[Citation]:
        citations: list[Citation] = []
        ref_pattern = re.findall(r"\[Source\s*(\d+)\]", content)

        for ref_num in set(ref_pattern):
            citations.append(
                Citation(
                    source=f"Source {ref_num}",
                    reference_number=int(ref_num),
                    relevance_score=1.0,
                )
            )

        bracket_refs = re.findall(r"\[(\d+)\]", content)
        for ref_num in set(bracket_refs):
            num = int(ref_num)
            if not any(c.reference_number == num for c in citations):
                citations.append(
                    Citation(
                        source=f"Reference {num}",
                        reference_number=num,
                        relevance_score=1.0,
                    )
                )

        return citations

    def _build_disclaimer(self, reasoning_plan: ReasoningPlan | None) -> str:
        if reasoning_plan and reasoning_plan.disclaimer and self._settings.RESPONSE_DISCLAIMER_ENABLED:
            return reasoning_plan.disclaimer
        return self._settings.RESPONSE_DISCLAIMER_TEXT if self._settings.RESPONSE_DISCLAIMER_ENABLED else ""

    def _extract_summary(self, sections: list[ClinicalSection], content: str) -> str:
        for section in sections:
            if section.section_type == ClinicalSectionType.SUMMARY:
                return section.content[:1000]
        if content:
            return content[:500]
        return ""

    def _format_text(self, content: str, sections: list[ClinicalSection]) -> str:
        if not self._settings.RESPONSE_SECTION_FORMATTING:
            return content
        parts: list[str] = []
        for section in sections:
            section_text = f"## {section.title}\n\n{section.content}"
            parts.append(section_text)
        return "\n\n".join(parts)

    def _format_final_answer(self, content: str, citations: list[Citation], disclaimer: str) -> str:
        parts = [content]

        if citations and self._settings.RESPONSE_CITATIONS_INLINE:
            refs = []
            seen: set[str] = set()
            for c in citations:
                if c.source not in seen:
                    refs.append(f"{c.reference_number}. {c.source}")
                    seen.add(c.source)
            if refs:
                parts.append("\n\n---\n**References:**\n" + "\n".join(refs))

        if disclaimer:
            parts.append(f"\n\n*{disclaimer}*")

        return "\n".join(parts)
