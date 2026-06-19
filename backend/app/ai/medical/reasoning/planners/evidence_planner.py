from app.ai.medical.engine.schemas import MedicalEntity, QueryUnderstandingResult
from app.ai.medical.reasoning.exceptions.exceptions import EvidencePlannerError
from app.ai.medical.reasoning.interfaces.interfaces import EvidencePlannerABC
from app.ai.medical.reasoning.schemas.schemas import (
    EvidencePlan,
    EvidencePriority,
    EvidenceRequirement,
    ReasoningPlan,
)

_EVIDENCE_QUERY_TEMPLATES: dict[str, list[str]] = {
    "symptom": [
        "{term} clinical presentation and characteristics",
        "{term} associated symptoms and signs",
        "{term} differential diagnosis considerations",
    ],
    "disease": [
        "{term} clinical guidelines and management",
        "{term} diagnosis and treatment protocols",
        "{term} prognosis and outcomes",
    ],
    "medication": [
        "{term} mechanism of action and indications",
        "{term} dosing and administration guidelines",
        "{term} side effects and contraindications",
    ],
    "procedure": [
        "{term} indications and contraindications",
        "{term} technique and complications",
        "{term} outcomes and recovery",
    ],
    "lab_test": [
        "{term} interpretation and reference ranges",
        "{term} clinical significance and follow-up",
    ],
    "anatomy": [
        "{term} anatomical关系和 clinical significance",
    ],
}

_ENTITY_TYPE_TOPIC_MAP: dict[str, str] = {
    "symptom": "symptom",
    "disease": "disease",
    "medication": "medication",
    "procedure": "procedure",
    "lab_test": "lab_test",
    "vital_sign": "symptom",
    "anatomy": "anatomy",
    "allergy": "medication",
    "dosage": "medication",
    "time_expression": "symptom",
    "age_reference": "symptom",
    "chronic_condition": "disease",
    "pregnancy_status": "disease",
}


class EvidencePlanner(EvidencePlannerABC):
    async def plan(
        self,
        query: str,
        analysis: QueryUnderstandingResult,
        reasoning_plan: ReasoningPlan,
    ) -> EvidencePlan:
        if not query or not query.strip():
            raise EvidencePlannerError("Query cannot be empty")

        requirements: list[EvidenceRequirement] = []
        queries: list[str] = [query]

        if analysis.rewrite and analysis.rewrite.rewritten_query:
            queries.append(analysis.rewrite.rewritten_query)

        if analysis.entities and analysis.entities.entities:
            for entity in analysis.entities.entities:
                req = self._build_requirement(entity, reasoning_plan)
                if req:
                    requirements.append(req)
                    queries.extend(req.query_variations)

        if analysis.specialty and analysis.specialty.primary_specialty:
            specialty = analysis.specialty.primary_specialty.specialty
            queries.append(f"{query} {specialty.replace('_', ' ')} clinical guidelines")

        requirements = self._deduplicate_requirements(requirements)
        queries = self._deduplicate_queries(queries)

        min_count = self._compute_min_evidence(reasoning_plan)
        max_count = 20

        priority_filters = {}
        if analysis.specialty and analysis.specialty.primary_specialty:
            priority_filters["specialty"] = analysis.specialty.primary_specialty.specialty

        return EvidencePlan(
            evidence_requirements=requirements,
            retrieval_queries=queries[:10],
            priority_filters=priority_filters,
            min_evidence_count=min_count,
            max_evidence_count=max_count,
        )

    def _build_requirement(
        self,
        entity: MedicalEntity,
        reasoning_plan: ReasoningPlan,
    ) -> EvidenceRequirement | None:
        topic_key = _ENTITY_TYPE_TOPIC_MAP.get(entity.entity_type.value)
        if not topic_key:
            return None

        templates = _EVIDENCE_QUERY_TEMPLATES.get(topic_key, ["{term}"])
        term = entity.normalized_text or entity.text
        variations = [t.format(term=term) for t in templates]

        priority = EvidencePriority.MEDIUM
        if topic_key in reasoning_plan.required_evidence_types:
            priority = EvidencePriority.HIGH
        if entity.entity_type.value in ("disease", "medication"):
            priority = EvidencePriority.ESSENTIAL if entity.confidence > 0.7 else EvidencePriority.HIGH

        return EvidenceRequirement(
            topic=term,
            priority=priority,
            query_variations=variations,
            min_results=2 if priority == EvidencePriority.ESSENTIAL else 1,
            required=priority == EvidencePriority.ESSENTIAL,
        )

    def _deduplicate_requirements(self, requirements: list[EvidenceRequirement]) -> list[EvidenceRequirement]:
        seen: set[str] = set()
        deduped: list[EvidenceRequirement] = []
        for req in requirements:
            key = req.topic.lower().strip()
            if key not in seen:
                seen.add(key)
                deduped.append(req)
        return deduped

    def _deduplicate_queries(self, queries: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for q in queries:
            key = q.lower().strip()
            if key not in seen:
                seen.add(key)
                deduped.append(q)
        return deduped

    def _compute_min_evidence(self, reasoning_plan: ReasoningPlan) -> int:
        base = 3
        if reasoning_plan.complexity_level == "advanced":
            base = 5
        elif reasoning_plan.complexity_level == "basic":
            base = 2
        return min(base, 10)
