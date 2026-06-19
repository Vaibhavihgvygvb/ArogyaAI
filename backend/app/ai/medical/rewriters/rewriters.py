import re

from app.ai.medical.interfaces.interfaces import QueryRewriterABC
from app.ai.medical.schemas.schemas import IntentType, MedicalIntent, QueryRewrite

_ABBREVIATIONS: dict[str, str] = {
    "sob": "shortness of breath",
    "cva": "cerebrovascular accident",
    "mi": "myocardial infarction",
    "htn": "hypertension",
    "dm": "diabetes mellitus",
    "copd": "chronic obstructive pulmonary disease",
    "uti": "urinary tract infection",
    "gi": "gastrointestinal",
    "gu": "genitourinary",
    "cxr": "chest x-ray",
    "ekg": "electrocardiogram",
    "lft": "liver function test",
    "bmp": "basic metabolic panel",
    "cbc": "complete blood count",
    "bp": "blood pressure",
    "hr": "heart rate",
    "rr": "respiratory rate",
    "temp": "temperature",
    "tbi": "traumatic brain injury",
    "cabg": "coronary artery bypass graft",
    "dvt": "deep vein thrombosis",
    "pe": "pulmonary embolism",
    "tia": "transient ischemic attack",
    "sbo": "small bowel obstruction",
}

_INTENT_EXPANSIONS: dict[IntentType, str] = {
    IntentType.DIAGNOSIS: "Provide a thorough analysis of potential diagnoses, including differential diagnoses, diagnostic criteria, and recommended diagnostic workup.",
    IntentType.TREATMENT: "Provide evidence-based treatment recommendations, including first-line therapies, alternative options, and treatment protocols.",
    IntentType.MEDICATION: "Provide detailed medication information including mechanism of action, dosing, side effects, contraindications, and drug interactions.",
    IntentType.SYMPTOM_ASSESSMENT: "Provide a comprehensive symptom assessment including typical presentation, red flags, associated symptoms, and clinical significance.",
    IntentType.PROCEDURE: "Provide detailed information about the procedure including indications, technique, risks, benefits, and post-procedure care.",
    IntentType.PREVENTION: "Provide evidence-based prevention strategies including screening recommendations, lifestyle modifications, and prophylactic measures.",
    IntentType.PROGNOSIS: "Provide prognosis information including expected clinical course, survival statistics, prognostic factors, and long-term outcomes.",
    IntentType.ETIOLOGY: "Provide information about etiology including causative factors, pathogenesis, risk factors, and underlying mechanisms.",
    IntentType.EPIDEMIOLOGY: "Provide epidemiological data including incidence, prevalence, demographics, and population health statistics.",
    IntentType.GENERAL_INQUIRY: "Provide a comprehensive overview including definition, clinical features, management, and key clinical considerations.",
}


class QueryRewriter(QueryRewriterABC):
    async def rewrite(self, query: str, intent: MedicalIntent, context: str | None = None) -> QueryRewrite:
        expansions = []
        abbreviations_expanded = []
        current_query = query

        expanded_abbrev, expanded_terms = self._expand_abbreviations(current_query)
        if expanded_abbrev != current_query:
            abbreviations_expanded = expanded_terms
            current_query = expanded_abbrev

        intent_instruction = _INTENT_EXPANSIONS.get(intent.intent_type, "")
        if intent_instruction:
            expansions.append(intent_instruction)

        context_injected = False
        if context and intent.specialty.value:
            specialty_clause = f"in the context of {intent.specialty.value.replace('_', ' ')}"
            if specialty_clause not in current_query.lower():
                current_query = f"{current_query} ({specialty_clause})"
                context_injected = True

        rewrite_reason = self._build_reason(abbreviations_expanded, expansions, context_injected)

        return QueryRewrite(
            original_query=query,
            rewritten_query=current_query,
            expansions=expansions,
            abbreviations_expanded=abbreviations_expanded,
            context_injected=context_injected,
            rewrite_reason=rewrite_reason,
        )

    def _expand_abbreviations(self, query: str) -> tuple[str, list[str]]:
        words = re.findall(r'\b[a-zA-Z.]+\b', query)
        expanded_terms = []
        result = query
        for word in words:
            clean_word = word.lower().strip(".")
            if clean_word in _ABBREVIATIONS:
                expanded = _ABBREVIATIONS[clean_word]
                expanded_terms.append(f"{word} → {expanded}")
                result = re.sub(
                    r'\b' + re.escape(word) + r'\b',
                    f"{word} ({expanded})",
                    result,
                    count=1,
                    flags=re.IGNORECASE,
                )
        return result, expanded_terms

    def _build_reason(
        self,
        abbreviations_expanded: list[str],
        expansions: list[str],
        context_injected: bool,
    ) -> str:
        parts = []
        if abbreviations_expanded:
            parts.append(f"Expanded {len(abbreviations_expanded)} abbreviation(s)")
        if expansions:
            parts.append("Added intent-specific context")
        if context_injected:
            parts.append("Injected specialty context")
        if not parts:
            return "No rewrite necessary"
        return "; ".join(parts)
