from app.ai.medical.interfaces.interfaces import MedicalReasonerABC
from app.ai.medical.schemas.schemas import IntentType, MedicalIntent, MedicalReasoning

_REASONING_TEMPLATES: dict[IntentType, str] = {
    IntentType.DIAGNOSIS: (
        "Clinical Reasoning for Diagnosis:\n"
        "1. Presenting symptoms and their significance\n"
        "2. Relevant history and risk factors\n"
        "3. Differential diagnoses considered\n"
        "4. Supporting evidence from retrieved knowledge\n"
        "5. Recommended diagnostic approach"
    ),
    IntentType.TREATMENT: (
        "Clinical Reasoning for Treatment:\n"
        "1. Disease characteristics and severity assessment\n"
        "2. First-line treatment options with evidence levels\n"
        "3. Alternative therapies and their indications\n"
        "4. Treatment monitoring parameters\n"
        "5. Expected outcomes and follow-up plan"
    ),
    IntentType.MEDICATION: (
        "Clinical Reasoning for Medication:\n"
        "1. Medication class and mechanism of action\n"
        "2. Evidence supporting use in this context\n"
        "3. Dosing considerations and adjustments\n"
        "4. Safety profile and monitoring requirements\n"
        "5. Drug interactions and contraindications"
    ),
    IntentType.SYMPTOM_ASSESSMENT: (
        "Clinical Reasoning for Symptom Assessment:\n"
        "1. Symptom characterization (onset, duration, quality)\n"
        "2. Associated signs and symptoms\n"
        "3. Red flags and warning signs\n"
        "4. Differential diagnostic considerations\n"
        "5. Recommended evaluation pathway"
    ),
}


class MedicalReasoner(MedicalReasonerABC):
    async def reason(
        self,
        query: str,
        context: str,
        response: str,
        intent: MedicalIntent,
    ) -> MedicalReasoning:
        template = _REASONING_TEMPLATES.get(intent.intent_type, "")
        chain_of_thought = self._build_chain_of_thought(query, context, response, intent, template)
        differential = self._extract_differential(response)
        limitations = self._identify_limitations(context, response, intent)
        evidence_summary = self._summarize_evidence(context, response)

        return MedicalReasoning(
            chain_of_thought=chain_of_thought,
            differential_considerations=differential,
            limitations=limitations,
            evidence_summary=evidence_summary,
        )

    def _build_chain_of_thought(
        self,
        query: str,
        context: str,
        response: str,
        intent: MedicalIntent,
        template: str,
    ) -> str:
        parts = ["## Chain of Thought"]
        if template:
            parts.append(template)
        parts.append(f"\n**Query Intent**: {intent.intent_type.value}")
        parts.append(f"**Specialty**: {intent.specialty.value}")
        parts.append(f"**Urgency**: {intent.urgency.value}")
        return "\n\n".join(parts)

    def _extract_differential(self, response: str) -> list[str]:
        import re

        considerations = []
        patterns = [
            r"(?:differential|consider|include|such as)[:\s]+([^.\n]+)",
            r"(?:diagnosis|condition|disorder)[:\s]+([^.\n]+)",
        ]
        for pattern in patterns:
            matches = re.findall(pattern, response, re.IGNORECASE)
            for m in matches:
                items = [item.strip() for item in re.split(r"[,;]| and | or ", m) if item.strip()]
                considerations.extend(items[:5])
        return considerations[:10]

    def _identify_limitations(self, context: str, response: str, intent: MedicalIntent) -> list[str]:
        limitations = []
        if not context or context.strip() == "":
            limitations.append("No knowledge base context was available for this response")
        if len(response.split()) < 50:
            limitations.append("Response is brief — may lack comprehensive detail")
        if intent.urgency in (intent.urgency.CRITICAL, intent.urgency.HIGH):
            limitations.append(
                "This is an informational response only — seek immediate professional medical care"
            )
        uncertainty_indicators = [
            "limited evidence", "insufficient data", "further research",
            "not well established", "unclear", "controversial",
        ]
        for indicator in uncertainty_indicators:
            if indicator in response.lower():
                limitations.append(f"Evidence base has noted limitations: {indicator}")
                break
        return limitations

    def _summarize_evidence(self, context: str, response: str) -> str:
        if not context:
            return "No evidence base retrieved for this response"
        context_sentences = [s.strip() for s in context.split(". ") if s.strip()]
        evidence_count = len(context_sentences)
        return f"This response is supported by {evidence_count} evidence segments from the medical knowledge base"
