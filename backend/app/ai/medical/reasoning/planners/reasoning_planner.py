from app.ai.medical.engine.schemas import IntentCandidate, QueryUnderstandingResult
from app.ai.medical.reasoning.exceptions.exceptions import ReasoningPlannerError
from app.ai.medical.reasoning.interfaces.interfaces import ReasoningPlannerABC
from app.ai.medical.reasoning.schemas.schemas import (
    ReasoningApproach,
    ReasoningPlan,
    ReasoningStep,
)

_APPROACH_MAP: dict[str, ReasoningApproach] = {
    "symptom_inquiry": ReasoningApproach.CLINICAL_REASONING,
    "disease_information": ReasoningApproach.EVIDENCE_SYNTHESIS,
    "medication_information": ReasoningApproach.EVIDENCE_SYNTHESIS,
    "prescription_explanation": ReasoningApproach.CONTEXTUAL_INFORMATION,
    "lab_report_interpretation": ReasoningApproach.CLINICAL_REASONING,
    "medical_record_explanation": ReasoningApproach.CONTEXTUAL_INFORMATION,
    "appointment_inquiry": ReasoningApproach.GENERAL_ANSWER,
    "preventive_care": ReasoningApproach.RISK_ASSESSMENT,
    "emergency": ReasoningApproach.RISK_ASSESSMENT,
    "mental_health": ReasoningApproach.CLINICAL_REASONING,
    "lifestyle_guidance": ReasoningApproach.CONTEXTUAL_INFORMATION,
    "nutrition": ReasoningApproach.CONTEXTUAL_INFORMATION,
    "vaccination": ReasoningApproach.EVIDENCE_SYNTHESIS,
    "follow_up": ReasoningApproach.GENERAL_ANSWER,
    "administrative": ReasoningApproach.GENERAL_ANSWER,
}

_STEP_TEMPLATES: dict[ReasoningApproach, list[str]] = {
    ReasoningApproach.CLINICAL_REASONING: [
        "Identify presenting symptoms and their clinical significance",
        "Review relevant history and risk factors",
        "Consider differential diagnoses based on symptom patterns",
        "Evaluate supporting evidence from medical knowledge base",
        "Synthesize clinical findings into structured assessment",
    ],
    ReasoningApproach.EVIDENCE_SYNTHESIS: [
        "Identify key clinical question and scope",
        "Retrieve relevant medical literature and guidelines",
        "Evaluate quality and recency of available evidence",
        "Synthesize findings across multiple sources",
        "Summarize evidence with strength-of-recommendation context",
    ],
    ReasoningApproach.COMPARATIVE_ANALYSIS: [
        "Identify options or conditions to compare",
        "Define comparison criteria and outcomes of interest",
        "Gather evidence for each option",
        "Evaluate relative benefits and risks",
        "Present comparative summary with evidence support",
    ],
    ReasoningApproach.DIFFERENTIAL_DIAGNOSIS: [
        "Catalog all possible diagnoses matching presentation",
        "Rank by likelihood based on epidemiology and risk factors",
        "Identify discriminating features between possibilities",
        "Suggest diagnostic tests to narrow differential",
        "Provide monitoring guidance for uncertain cases",
    ],
    ReasoningApproach.TREATMENT_PLANNING: [
        "Assess disease characteristics and severity",
        "Review first-line and alternative treatment options",
        "Evaluate patient-specific considerations and contraindications",
        "Define treatment monitoring parameters and endpoints",
        "Outline follow-up and escalation plan",
    ],
    ReasoningApproach.RISK_ASSESSMENT: [
        "Identify risk factors from query and patient context",
        "Evaluate probability and severity of adverse outcomes",
        "Review preventive and mitigative strategies",
        "Provide risk-stratified recommendations",
        "Flag urgent or emergent concerns requiring immediate attention",
    ],
    ReasoningApproach.CONTEXTUAL_INFORMATION: [
        "Determine the specific information being requested",
        "Retrieve relevant context and background",
        "Organize information in a clear, structured format",
        "Explain terminology and clinical relevance",
        "Provide actionable next steps where applicable",
    ],
    ReasoningApproach.GENERAL_ANSWER: [
        "Understand the general nature of the query",
        "Retrieve broadly relevant medical information",
        "Provide clear, well-organized response",
        "Include appropriate context and disclaimers",
        "Suggest follow-up questions or clarifications if needed",
    ],
}

_COMPLEXITY_MAP: dict[str, str] = {
    "patient": "basic",
    "caregiver": "basic",
    "nurse": "intermediate",
    "doctor": "advanced",
    "administrator": "intermediate",
    "unknown": "intermediate",
}

_EVIDENCE_TYPES: dict[ReasoningApproach, list[str]] = {
    ReasoningApproach.CLINICAL_REASONING: [
        "symptom_patterns", "risk_factors", "differential_diagnoses",
    ],
    ReasoningApproach.EVIDENCE_SYNTHESIS: [
        "clinical_guidelines", "research_studies", "expert_consensus",
    ],
    ReasoningApproach.COMPARATIVE_ANALYSIS: [
        "comparative_studies", "outcome_data", "safety_profiles",
    ],
    ReasoningApproach.DIFFERENTIAL_DIAGNOSIS: [
        "diagnostic_criteria", "prevalence_data", "test_characteristics",
    ],
    ReasoningApproach.TREATMENT_PLANNING: [
        "treatment_guidelines", "contraindications", "monitoring_protocols",
    ],
    ReasoningApproach.RISK_ASSESSMENT: [
        "risk_factors", "preventive_guidelines", "screening_protocols",
    ],
    ReasoningApproach.CONTEXTUAL_INFORMATION: [
        "background_information", "terminology", "clinical_context",
    ],
    ReasoningApproach.GENERAL_ANSWER: [
        "general_information", "patient_education",
    ],
}


class ReasoningPlanner(ReasoningPlannerABC):
    async def plan(
        self,
        query: str,
        analysis: QueryUnderstandingResult,
        approach_hint: str | None = None,
    ) -> ReasoningPlan:
        if not query or not query.strip():
            raise ReasoningPlannerError("Query cannot be empty")

        approach = self._determine_approach(analysis, approach_hint)
        steps = self._build_steps(approach)
        evidence_types = _EVIDENCE_TYPES.get(approach, [])
        audience = self._resolve_audience(analysis)
        complexity = _COMPLEXITY_MAP.get(audience, "intermediate")
        output_structure = self._build_output_structure(approach)

        return ReasoningPlan(
            approach=approach,
            reasoning_steps=steps,
            required_evidence_types=evidence_types,
            output_structure=output_structure,
            target_audience=audience,
            complexity_level=complexity,
        )

    def _determine_approach(
        self,
        analysis: QueryUnderstandingResult,
        approach_hint: str | None,
    ) -> ReasoningApproach:
        if approach_hint:
            try:
                return ReasoningApproach(approach_hint)
            except ValueError:
                pass

        if analysis.intent and analysis.intent.primary_intent:
            intent_type = analysis.intent.primary_intent.intent_type
            mapped = _APPROACH_MAP.get(intent_type)
            if mapped:
                return mapped

        if analysis.urgency and analysis.urgency.is_emergency:
            return ReasoningApproach.RISK_ASSESSMENT

        return ReasoningApproach.EVIDENCE_SYNTHESIS

    def _build_steps(self, approach: ReasoningApproach) -> list[ReasoningStep]:
        templates = _STEP_TEMPLATES.get(approach, _STEP_TEMPLATES[ReasoningApproach.GENERAL_ANSWER])
        return [
            ReasoningStep(step_number=i + 1, description=desc)
            for i, desc in enumerate(templates)
        ]

    def _resolve_audience(self, analysis: QueryUnderstandingResult) -> str:
        if analysis.audience:
            return analysis.audience.audience.value
        return "unknown"

    def _build_output_structure(self, approach: ReasoningApproach) -> dict:
        base = {
            "summary": "string",
            "key_findings": "list[string]",
        }
        structures = {
            ReasoningApproach.CLINICAL_REASONING: {
                **base,
                "symptom_analysis": "object",
                "differential_considerations": "list[string]",
                "recommended_approach": "string",
            },
            ReasoningApproach.EVIDENCE_SYNTHESIS: {
                **base,
                "evidence_levels": "object",
                "sources": "list[string]",
                "strength_of_recommendation": "string",
            },
            ReasoningApproach.DIFFERENTIAL_DIAGNOSIS: {
                **base,
                "differential_list": "list[object]",
                "discriminating_factors": "object",
                "recommended_tests": "list[string]",
            },
            ReasoningApproach.TREATMENT_PLANNING: {
                **base,
                "treatment_options": "list[object]",
                "monitoring_parameters": "list[string]",
                "follow_up_plan": "string",
            },
            ReasoningApproach.RISK_ASSESSMENT: {
                **base,
                "risk_factors": "list[object]",
                "risk_level": "string",
                "preventive_measures": "list[string]",
                "urgent_concerns": "list[string]",
            },
        }
        return structures.get(approach, base)
