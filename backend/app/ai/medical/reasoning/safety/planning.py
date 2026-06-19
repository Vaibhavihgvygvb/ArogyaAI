from app.ai.medical.engine.schemas import QueryUnderstandingResult
from app.ai.medical.reasoning.exceptions.exceptions import SafetyPlanningError
from app.ai.medical.reasoning.interfaces.interfaces import SafetyPlannerABC
from app.ai.medical.reasoning.schemas.schemas import ReasoningPlan, SafetyPlan

_URGENCY_DISCLAIMERS: dict[str, list[str]] = {
    "emergency": [
        "THIS IS AN EMERGENCY — If you are experiencing a medical emergency, call your local emergency services immediately.",
        "Do not wait for an online response. Seek immediate medical attention.",
        "This information is not a substitute for emergency medical care.",
    ],
    "urgent": [
        "This condition may require timely medical attention. Please consult a healthcare provider promptly.",
        "If symptoms worsen or you experience new severe symptoms, seek emergency care immediately.",
    ],
    "routine": [
        "This information is for educational purposes only and does not constitute medical advice.",
        "Always consult a qualified healthcare professional for medical decisions.",
    ],
}

_DANGEROUS_TOPIC_PATTERNS = [
    "suicide",
    "self-harm",
    "self harm",
    "overdose",
    "euthanasia",
    "assisted suicide",
]


class SafetyPlanner(SafetyPlannerABC):
    async def plan(
        self,
        query: str,
        analysis: QueryUnderstandingResult,
        reasoning_plan: ReasoningPlan,
    ) -> SafetyPlan:
        if not query or not query.strip():
            raise SafetyPlanningError("Query cannot be empty")

        constraints = self._build_constraints(analysis, reasoning_plan)
        required_checks = self._build_required_checks(analysis, reasoning_plan)
        disclaimers = self._build_disclaimers(analysis)
        prohibited = self._identify_prohibited_content(query, analysis)

        return SafetyPlan(
            constraints=constraints,
            required_checks=required_checks,
            disclaimers=disclaimers,
            prohibited_content_patterns=prohibited,
        )

    def _build_constraints(
        self,
        analysis: QueryUnderstandingResult,
        reasoning_plan: ReasoningPlan,
    ) -> list[str]:
        constraints = [
            "Do not provide definitive diagnoses — this is informational only",
            "Do not prescribe or recommend specific medications or dosages",
            "Do not replace professional medical advice",
            "Base answers only on provided medical context",
            "Flag information requiring immediate medical attention",
        ]

        if analysis.urgency and analysis.urgency.is_emergency:
            constraints.insert(0, "URGENT: Prioritize emergency disclaimer and immediate care guidance")
            constraints.append("Include emergency service contact information")

        audience = reasoning_plan.target_audience
        if analysis.audience and analysis.audience.audience.value != "unknown":
            audience = analysis.audience.audience.value

        if audience == "patient":
            constraints.append("Explain medical terminology in plain language")
            constraints.append("Include 'consult your doctor' recommendations")
        elif audience == "doctor":
            constraints.append("Use precise clinical terminology")
            constraints.append("Include evidence levels and citations")

        return constraints

    def _build_required_checks(
        self,
        analysis: QueryUnderstandingResult,
        reasoning_plan: ReasoningPlan,
    ) -> list[str]:
        checks = [
            "validate_input_safety",
            "detect_hallucination_risk",
            "check_unsafe_advice",
        ]

        if analysis.urgency and analysis.urgency.is_emergency:
            checks.append("validate_emergency_response")
            checks.append("verify_disclaimer_prominence")

        if reasoning_plan.approach.value in ("treatment_planning", "medication_information"):
            checks.append("verify_dosage_safety")
            checks.append("check_contraindications")

        if reasoning_plan.target_audience == "patient":
            checks.append("verify_patient_appropriate_language")

        return checks

    def _build_disclaimers(
        self,
        analysis: QueryUnderstandingResult,
    ) -> list[str]:
        urgency_level = "routine"
        if analysis.urgency:
            if analysis.urgency.is_emergency:
                urgency_level = "emergency"
            else:
                urgency_level = analysis.urgency.level

        return _URGENCY_DISCLAIMERS.get(urgency_level, _URGENCY_DISCLAIMERS["routine"])

    def _identify_prohibited_content(
        self,
        query: str,
        analysis: QueryUnderstandingResult,
    ) -> list[str]:
        detected: list[str] = []
        query_lower = query.lower()

        for pattern in _DANGEROUS_TOPIC_PATTERNS:
            if pattern in query_lower:
                detected.append(pattern)

        if analysis.intent and analysis.intent.primary_intent:
            if analysis.intent.primary_intent.intent_type == "emergency":
                detected.append("emergency_response_required")

        return detected
