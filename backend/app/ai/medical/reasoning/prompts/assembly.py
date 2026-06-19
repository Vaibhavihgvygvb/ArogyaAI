from app.ai.medical.engine.schemas import QueryUnderstandingResult
from app.ai.medical.reasoning.exceptions.exceptions import PromptAssemblyError
from app.ai.medical.reasoning.interfaces.interfaces import PromptAssemblerABC
from app.ai.medical.reasoning.schemas.schemas import (
    AssembledPrompt,
    CompressedContext,
    EvidencePlan,
    ReasoningApproach,
    ReasoningPlan,
)

_DEFAULT_SYSTEM_MESSAGE = """You are a medical intelligence assistant providing evidence-based clinical information.

Medical Context:
{context}

Reasoning Approach: {approach}
Target Audience: {audience}
Complexity Level: {complexity}

Guidelines:
- Answer based ONLY on the provided medical context
- If the context lacks sufficient information, state this clearly
- Do NOT provide definitive diagnoses or treatment plans — this is informational only
- Flag any information that requires immediate medical attention
- Use precise medical terminology but explain complex terms
- Cite specific sources when referencing information from the context
- Distinguish between established medical knowledge and emerging research"""

_APPROACH_INSTRUCTIONS: dict[ReasoningApproach, str] = {
    ReasoningApproach.CLINICAL_REASONING: (
        "Apply systematic clinical reasoning. Evaluate symptoms, history, and risk factors. "
        "Consider differential diagnoses and evidence support."
    ),
    ReasoningApproach.EVIDENCE_SYNTHESIS: (
        "Synthesize evidence from multiple sources. Evaluate quality and recency of available evidence. "
        "Present findings with strength-of-recommendation context."
    ),
    ReasoningApproach.COMPARATIVE_ANALYSIS: (
        "Compare options systematically. Define criteria, evaluate relative benefits and risks. "
        "Present balanced comparative summary."
    ),
    ReasoningApproach.DIFFERENTIAL_DIAGNOSIS: (
        "Build structured differential diagnosis. Rank by likelihood, identify discriminating features, "
        "suggest diagnostic approaches."
    ),
    ReasoningApproach.TREATMENT_PLANNING: (
        "Outline evidence-based treatment approach. Consider first-line and alternative options, "
        "patient-specific factors, monitoring parameters."
    ),
    ReasoningApproach.RISK_ASSESSMENT: (
        "Assess risks systematically. Identify risk factors, evaluate probability and severity, "
        "recommend preventive strategies. Flag urgent concerns."
    ),
    ReasoningApproach.CONTEXTUAL_INFORMATION: (
        "Provide clear contextual medical information. Explain terminology, clinical relevance, "
        "and actionable next steps."
    ),
    ReasoningApproach.GENERAL_ANSWER: (
        "Provide clear, well-organized medical information. Include appropriate context, "
        "disclaimers, and suggest follow-up questions if needed."
    ),
}


class PromptAssembler(PromptAssemblerABC):
    async def assemble(
        self,
        query: str,
        compressed_context: CompressedContext,
        reasoning_plan: ReasoningPlan,
        evidence_plan: EvidencePlan,
        analysis: QueryUnderstandingResult,
    ) -> AssembledPrompt:
        if not query or not query.strip():
            raise PromptAssemblyError("Query cannot be empty")

        variables = self._build_variables(query, compressed_context, reasoning_plan, evidence_plan, analysis)
        system_message = _DEFAULT_SYSTEM_MESSAGE.format(**variables)

        user_prompt = self._build_user_prompt(query, reasoning_plan, analysis)
        token_count = (len(system_message) + len(user_prompt)) // 4

        return AssembledPrompt(
            system_message=system_message,
            user_prompt=user_prompt,
            prompt_name="medical_reasoning",
            prompt_version="1.0.0",
            token_count=max(1, token_count),
            variables=variables,
        )

    def _build_variables(
        self,
        query: str,
        compressed_context: CompressedContext,
        reasoning_plan: ReasoningPlan,
        evidence_plan: EvidencePlan,
        analysis: QueryUnderstandingResult,
    ) -> dict:
        return {
            "context": compressed_context.context or "No medical context available.",
            "approach": _APPROACH_INSTRUCTIONS.get(
                reasoning_plan.approach,
                "Provide accurate medical information based on available evidence.",
            ),
            "audience": reasoning_plan.target_audience,
            "complexity": reasoning_plan.complexity_level,
            "query": query,
            "evidence_count": str(len(evidence_plan.evidence_requirements)),
            "specialty": (
                analysis.specialty.primary_specialty.specialty.replace("_", " ").title()
                if analysis.specialty and analysis.specialty.primary_specialty
                else "General Medicine"
            ),
            "urgency": (
                analysis.urgency.level.title()
                if analysis.urgency
                else "Routine"
            ),
        }

    def _build_user_prompt(
        self,
        query: str,
        reasoning_plan: ReasoningPlan,
        analysis: QueryUnderstandingResult,
    ) -> str:
        parts = [f"**Medical Query**: {query}"]

        if analysis.specialty and analysis.specialty.primary_specialty:
            specialty_name = analysis.specialty.primary_specialty.specialty.replace("_", " ").title()
            parts.append(f"**Specialty Context**: {specialty_name}")

        if analysis.urgency:
            parts.append(f"**Urgency Level**: {analysis.urgency.level.title()}")

        parts.append(f"**Reasoning Approach**: {reasoning_plan.approach.value.replace('_', ' ').title()}")
        parts.append(f"**Target Audience**: {reasoning_plan.target_audience.title()}")

        if reasoning_plan.reasoning_steps:
            steps = "\n".join(
                f"{s.step_number}. {s.description}"
                for s in reasoning_plan.reasoning_steps
            )
            parts.append(f"**Reasoning Steps**:\n{steps}")

        return "\n\n".join(parts)
