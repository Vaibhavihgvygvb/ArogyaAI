import pytest

from app.ai.medical.engine.schemas import (
    AudienceResult,
    AudienceType,
    EntityResult,
    IntentCandidate,
    IntentResult,
    LanguageInfo,
    MedicalEntity,
    EntityType,
    QueryUnderstandingResult,
    RewriteResult,
    SpecialtyCandidate,
    SpecialtyResult,
    UrgencyResult,
)
from app.ai.medical.reasoning.citations.planning import CitationPlanner
from app.ai.medical.reasoning.config.config import ReasoningSettings
from app.ai.medical.reasoning.confidence.planning import ConfidencePlanner
from app.ai.medical.reasoning.context.compression import ContextCompressor
from app.ai.medical.reasoning.context.ranking import ContextRanker
from app.ai.medical.reasoning.exceptions.exceptions import (
    CitationPlanningError,
    ConfidencePlanningError,
    ContextCompressionError,
    ContextRankingError,
    EvidencePlannerError,
    PromptAssemblyError,
    ReasoningPlannerError,
    RetrievalStrategyError,
    SafetyPlanningError,
)
from app.ai.medical.reasoning.pipelines.pipelines import ReasoningPipeline
from app.ai.medical.reasoning.planners.evidence_planner import EvidencePlanner
from app.ai.medical.reasoning.planners.reasoning_planner import ReasoningPlanner
from app.ai.medical.reasoning.planners.retrieval_strategy import RetrievalStrategy
from app.ai.medical.reasoning.prompts.assembly import PromptAssembler
from app.ai.medical.reasoning.safety.planning import SafetyPlanner
from app.ai.medical.reasoning.schemas.schemas import (
    AssembledPrompt,
    CitationPlan,
    CompressedContext,
    CompressionStrategy,
    ConfidencePlan,
    EvidencePlan,
    EvidencePriority,
    EvidenceRequirement,
    RankedContext,
    ReasoningApproach,
    ReasoningPlan,
    ReasoningRequest,
    ReasoningResponse,
    ReasoningStep,
    RetrievalPlan,
    RetrievalStrategyType,
    SafetyPlan,
)
from app.ai.medical.reasoning.services.services import ReasoningService
from app.ai.medical.reasoning.exceptions.exceptions import ReasoningServiceError
from app.ai.medical.engine.deps import reset_query_understanding_engine
from app.ai.retrieval.deps.deps import reset_retrieval_service


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_singletons():
    reset_query_understanding_engine()
    reset_retrieval_service()
    yield

@pytest.fixture
def sample_analysis() -> QueryUnderstandingResult:
    return QueryUnderstandingResult(
        original_query="What are the symptoms and treatment for type 2 diabetes?",
        intent=IntentResult(
            primary_intent=IntentCandidate(
                intent_type="disease_information",
                confidence=0.92,
                matched_keywords=["symptoms", "treatment", "diabetes"],
            ),
            candidates=[
                IntentCandidate(intent_type="disease_information", confidence=0.92),
                IntentCandidate(intent_type="medication_information", confidence=0.45),
            ],
            total_candidates=2,
        ),
        entities=EntityResult(
            entities=[
                MedicalEntity(
                    entity_type=EntityType.DISEASE,
                    text="type 2 diabetes",
                    normalized_text="type 2 diabetes mellitus",
                    confidence=0.95,
                    start_pos=35,
                    end_pos=50,
                ),
                MedicalEntity(
                    entity_type=EntityType.SYMPTOM,
                    text="symptoms",
                    normalized_text="symptoms",
                    confidence=0.85,
                    start_pos=19,
                    end_pos=27,
                ),
            ],
            total=2,
        ),
        specialty=SpecialtyResult(
            primary_specialty=SpecialtyCandidate(
                specialty="endocrinology",
                confidence=0.88,
                matched_terms=["diabetes", "type 2 diabetes"],
            ),
            candidates=[SpecialtyCandidate(specialty="endocrinology", confidence=0.88)],
            total_candidates=1,
        ),
        urgency=UrgencyResult(
            level="routine",
            confidence=0.75,
            indicators=["follow_up", "checkup"],
            is_emergency=False,
        ),
        audience=AudienceResult(
            audience=AudienceType.PATIENT,
            confidence=0.85,
            indicators=["what are the symptoms", "treatment for"],
        ),
        language=LanguageInfo(
            language="en",
            confidence=0.99,
            has_abbreviations=False,
            has_acronyms=False,
        ),
        rewrite=RewriteResult(
            original_query="What are the symptoms and treatment for type 2 diabetes?",
            rewritten_query="What are the clinical manifestations and management protocols for type 2 diabetes mellitus?",
            expansions=["clinical manifestations", "management protocols", "type 2 diabetes mellitus"],
            abbreviations_expanded=[],
            normalized=True,
        ),
        analysis_scope="full",
    )


@pytest.fixture
def emergency_analysis() -> QueryUnderstandingResult:
    return QueryUnderstandingResult(
        original_query="I am having chest pain and difficulty breathing",
        intent=IntentResult(
            primary_intent=IntentCandidate(
                intent_type="emergency",
                confidence=0.95,
                matched_keywords=["chest pain", "difficulty breathing"],
            ),
            candidates=[IntentCandidate(intent_type="emergency", confidence=0.95)],
            total_candidates=1,
        ),
        entities=EntityResult(
            entities=[
                MedicalEntity(
                    entity_type=EntityType.SYMPTOM,
                    text="chest pain",
                    normalized_text="chest pain",
                    confidence=0.95,
                    start_pos=13,
                    end_pos=23,
                ),
                MedicalEntity(
                    entity_type=EntityType.SYMPTOM,
                    text="difficulty breathing",
                    normalized_text="dyspnea",
                    confidence=0.90,
                    start_pos=28,
                    end_pos=47,
                ),
            ],
            total=2,
        ),
        specialty=SpecialtyResult(
            primary_specialty=SpecialtyCandidate(
                specialty="emergency_medicine",
                confidence=0.92,
                matched_terms=["chest pain", "difficulty breathing"],
            ),
            total_candidates=1,
        ),
        urgency=UrgencyResult(
            level="emergency",
            confidence=0.95,
            indicators=["chest pain", "difficulty breathing", "emergency"],
            is_emergency=True,
        ),
        audience=AudienceResult(
            audience=AudienceType.PATIENT,
            confidence=0.90,
            indicators=["I am having"],
        ),
        language=LanguageInfo(language="en", confidence=0.99),
        analysis_scope="full",
    )


@pytest.fixture
def sample_results():
    class MockResult:
        def __init__(self, chunk_id, knowledge_id, content, score, metadata=None):
            self.chunk_id = chunk_id
            self.knowledge_id = knowledge_id
            self.content = content
            self.score = score
            self.metadata = metadata or {"source": "test", "document_id": "doc1"}
            self.evidence_text = content

    return [
        MockResult(
            "chunk_1", "know_1",
            "Type 2 diabetes mellitus is a chronic metabolic disorder characterized by insulin resistance and relative insulin deficiency. Common symptoms include polyuria, polydipsia, and weight loss.",
            0.92,
        ),
        MockResult(
            "chunk_2", "know_2",
            "First-line treatment for type 2 diabetes includes metformin monotherapy along with lifestyle modifications including diet and exercise.",
            0.88,
        ),
        MockResult(
            "chunk_3", "know_3",
            "HbA1c targets for most adults with type 2 diabetes are less than 7.0%. Monitoring should occur at least twice yearly for stable patients.",
            0.75,
        ),
        MockResult(
            "chunk_4", "know_4",
            "Complications of uncontrolled diabetes include neuropathy, nephropathy, retinopathy, and cardiovascular disease.",
            0.70,
        ),
        MockResult(
            "chunk_5", "know_5",
            "Insulin therapy may be required when oral agents fail to achieve glycemic targets. Basal insulin is typically initiated at 0.1-0.2 units/kg/day.",
            0.65,
        ),
    ]


# ---------------------------------------------------------------------------
# ReasoningPlanner Tests
# ---------------------------------------------------------------------------

class TestReasoningPlanner:
    @pytest.fixture
    def planner(self):
        return ReasoningPlanner()

    async def test_plan_with_disease_information_intent(self, planner, sample_analysis):
        plan = await planner.plan("What are the symptoms and treatment for type 2 diabetes?", sample_analysis)
        assert plan.approach == ReasoningApproach.EVIDENCE_SYNTHESIS
        assert len(plan.reasoning_steps) > 0
        assert len(plan.required_evidence_types) > 0
        assert plan.target_audience == "patient"

    async def test_plan_with_emergency_intent(self, planner, emergency_analysis):
        plan = await planner.plan("I am having chest pain and difficulty breathing", emergency_analysis)
        assert plan.approach == ReasoningApproach.RISK_ASSESSMENT
        assert plan.complexity_level == "basic"

    async def test_plan_with_approach_hint(self, planner, sample_analysis):
        plan = await planner.plan(
            "What are the symptoms and treatment for type 2 diabetes?",
            sample_analysis,
            approach_hint="clinical_reasoning",
        )
        assert plan.approach == ReasoningApproach.CLINICAL_REASONING

    async def test_plan_with_invalid_hint(self, planner, sample_analysis):
        plan = await planner.plan("test", sample_analysis, approach_hint="invalid_approach")
        assert plan.approach == ReasoningApproach.EVIDENCE_SYNTHESIS

    async def test_plan_empty_query(self, planner, sample_analysis):
        with pytest.raises(ReasoningPlannerError):
            await planner.plan("", sample_analysis)

    async def test_plan_whitespace_query(self, planner, sample_analysis):
        with pytest.raises(ReasoningPlannerError):
            await planner.plan("   ", sample_analysis)

    async def test_plan_approach_determination_all_intents(self, planner, sample_analysis):
        from app.ai.medical.reasoning.planners.reasoning_planner import _APPROACH_MAP

        for intent_type, expected_approach in _APPROACH_MAP.items():
            custom_analysis = QueryUnderstandingResult(
                original_query=f"test {intent_type}",
                intent=IntentResult(
                    primary_intent=IntentCandidate(
                        intent_type=intent_type,
                        confidence=0.9,
                    ),
                    total_candidates=1,
                ),
                specialty=SpecialtyResult(
                    primary_specialty=SpecialtyCandidate(specialty="general_medicine", confidence=0.5),
                    total_candidates=1,
                ),
                urgency=UrgencyResult(level="routine"),
                audience=AudienceResult(audience=AudienceType.UNKNOWN),
                language=LanguageInfo(language="en"),
                analysis_scope="full",
            )
            plan = await planner.plan(f"test {intent_type}", custom_analysis)
            assert plan.approach == expected_approach, f"Failed for intent_type={intent_type}"

    async def test_plan_steps_always_present(self, planner, sample_analysis):
        plan = await planner.plan("test query", sample_analysis)
        assert len(plan.reasoning_steps) >= 3
        for step in plan.reasoning_steps:
            assert step.step_number >= 1
            assert step.description
            assert step.status == "pending"

    async def test_plan_output_structure(self, planner, sample_analysis):
        plan = await planner.plan("test query", sample_analysis)
        assert isinstance(plan.output_structure, dict)
        assert "summary" in plan.output_structure or plan.approach == ReasoningApproach.GENERAL_ANSWER

    async def test_plan_complexity_audience_mapping(self, planner, sample_analysis):
        plan = await planner.plan("What are the symptoms and treatment for type 2 diabetes?", sample_analysis)
        assert plan.target_audience == "patient"
        assert plan.complexity_level == "basic"

    async def test_plan_doctor_audience(self, planner):
        doctor_analysis = QueryUnderstandingResult(
            original_query="What is the mechanism of action of metformin?",
            audience=AudienceResult(audience=AudienceType.DOCTOR, confidence=0.9),
            language=LanguageInfo(language="en"),
            analysis_scope="full",
        )
        plan = await planner.plan("What is the mechanism of action of metformin?", doctor_analysis)
        assert plan.target_audience == "doctor"
        assert plan.complexity_level == "advanced"


# ---------------------------------------------------------------------------
# EvidencePlanner Tests
# ---------------------------------------------------------------------------

class TestEvidencePlanner:
    @pytest.fixture
    def planner(self):
        return EvidencePlanner()

    @pytest.fixture
    def reasoning_plan(self):
        return ReasoningPlan(
            approach=ReasoningApproach.EVIDENCE_SYNTHESIS,
            reasoning_steps=[
                ReasoningStep(step_number=1, description="Identify key clinical question"),
            ],
            required_evidence_types=["clinical_guidelines", "research_studies"],
            target_audience="patient",
        )

    async def test_plan_with_entities(self, planner, sample_analysis, reasoning_plan):
        ev_plan = await planner.plan("test", sample_analysis, reasoning_plan)
        assert len(ev_plan.evidence_requirements) > 0
        assert len(ev_plan.retrieval_queries) > 0
        assert ev_plan.min_evidence_count > 0

    async def test_plan_empty_query(self, planner, sample_analysis, reasoning_plan):
        with pytest.raises(EvidencePlannerError):
            await planner.plan("", sample_analysis, reasoning_plan)

    async def test_plan_includes_original_and_rewritten_queries(self, planner, sample_analysis, reasoning_plan):
        ev_plan = await planner.plan("test query", sample_analysis, reasoning_plan)
        assert "test query" in ev_plan.retrieval_queries

    async def test_plan_no_entities(self, planner, reasoning_plan):
        minimal = QueryUnderstandingResult(
            original_query="test",
            language=LanguageInfo(language="en"),
            analysis_scope="full",
        )
        ev_plan = await planner.plan("test", minimal, reasoning_plan)
        assert len(ev_plan.retrieval_queries) >= 1

    async def test_plan_deduplicates_requirements(self, planner, reasoning_plan):
        analysis = QueryUnderstandingResult(
            original_query="test diabetes diabetes",
            entities=EntityResult(
                entities=[
                    MedicalEntity(entity_type=EntityType.DISEASE, text="diabetes", normalized_text="diabetes", confidence=0.9, start_pos=0, end_pos=8),
                    MedicalEntity(entity_type=EntityType.DISEASE, text="diabetes", normalized_text="diabetes", confidence=0.8, start_pos=9, end_pos=17),
                ],
                total=2,
            ),
            language=LanguageInfo(language="en"),
            analysis_scope="full",
        )
        ev_plan = await planner.plan("test diabetes diabetes", analysis, reasoning_plan)
        diabetes_reqs = [r for r in ev_plan.evidence_requirements if "diabetes" in r.topic.lower()]
        assert len(diabetes_reqs) <= 1

    async def test_plan_essential_priority_for_high_confidence_disease(self, planner, reasoning_plan):
        analysis = QueryUnderstandingResult(
            original_query="test diabetes",
            entities=EntityResult(
                entities=[
                    MedicalEntity(entity_type=EntityType.DISEASE, text="diabetes", normalized_text="diabetes", confidence=0.85, start_pos=0, end_pos=8),
                ],
                total=1,
            ),
            language=LanguageInfo(language="en"),
            analysis_scope="full",
        )
        ev_plan = await planner.plan("test diabetes", analysis, reasoning_plan)
        diabetes_reqs = [r for r in ev_plan.evidence_requirements if r.topic == "diabetes"]
        if diabetes_reqs:
            assert diabetes_reqs[0].priority in (EvidencePriority.ESSENTIAL, EvidencePriority.HIGH)

    async def test_plan_min_evidence_count(self, planner, sample_analysis, reasoning_plan):
        ev_plan = await planner.plan("test", sample_analysis, reasoning_plan)
        assert ev_plan.min_evidence_count >= 2

    async def test_plan_priority_filters_from_specialty(self, planner, sample_analysis, reasoning_plan):
        ev_plan = await planner.plan("test", sample_analysis, reasoning_plan)
        assert "specialty" in ev_plan.priority_filters


# ---------------------------------------------------------------------------
# RetrievalStrategy Tests
# ---------------------------------------------------------------------------

class TestRetrievalStrategy:
    @pytest.fixture
    def strategy(self):
        return RetrievalStrategy()

    @pytest.fixture
    def evidence_plan(self):
        return EvidencePlan(
            evidence_requirements=[
                EvidenceRequirement(topic="diabetes", priority=EvidencePriority.ESSENTIAL, query_variations=["diabetes symptoms", "diabetes treatment"], required=True),
                EvidenceRequirement(topic="metformin", priority=EvidencePriority.HIGH, query_variations=["metformin mechanism", "metformin dosing"]),
            ],
            retrieval_queries=["diabetes symptoms", "diabetes treatment", "metformin mechanism"],
            priority_filters={"specialty": "endocrinology"},
        )

    async def test_plan_with_evidence(self, strategy, evidence_plan, sample_analysis):
        plan = await strategy.plan("test", evidence_plan, sample_analysis)
        assert len(plan.sub_queries) > 0
        assert plan.top_k_per_query > 0
        assert isinstance(plan.strategy, RetrievalStrategyType)

    async def test_plan_empty_query(self, strategy, evidence_plan, sample_analysis):
        with pytest.raises(RetrievalStrategyError):
            await strategy.plan("", evidence_plan, sample_analysis)

    async def test_plan_single_query_strategy(self, strategy, sample_analysis):
        empty_plan = EvidencePlan(retrieval_queries=["test"], min_evidence_count=1)
        plan = await strategy.plan("test", empty_plan, sample_analysis)
        assert plan.strategy == RetrievalStrategyType.SINGLE

    async def test_plan_parallel_strategy_for_emergency(self, strategy, evidence_plan, emergency_analysis):
        plan = await strategy.plan("emergency", evidence_plan, emergency_analysis)
        assert plan.strategy == RetrievalStrategyType.PARALLEL

    async def test_plan_hierarchical_strategy_for_many_queries(self, strategy, sample_analysis):
        many_queries = EvidencePlan(
            retrieval_queries=[f"query_{i}" for i in range(5)],
            min_evidence_count=3,
        )
        plan = await strategy.plan("test", many_queries, sample_analysis)
        assert plan.strategy in (RetrievalStrategyType.PARALLEL, RetrievalStrategyType.HIERARCHICAL)

    async def test_plan_weights_positive(self, strategy, evidence_plan, sample_analysis):
        plan = await strategy.plan("test", evidence_plan, sample_analysis)
        for w in plan.weights:
            assert w > 0

    async def test_plan_filters_merged(self, strategy, evidence_plan, sample_analysis):
        plan = await strategy.plan("test", evidence_plan, sample_analysis, filters={"extra": "filter"})
        assert plan.filters is not None
        assert plan.filters.get("specialty") == "endocrinology"
        assert plan.filters.get("extra") == "filter"

    async def test_plan_top_k_distribution(self, strategy, evidence_plan, sample_analysis):
        plan = await strategy.plan("test", evidence_plan, sample_analysis, top_k=30)
        assert plan.top_k_per_query <= 20


# ---------------------------------------------------------------------------
# ContextRanker Tests
# ---------------------------------------------------------------------------

class TestContextRanker:
    @pytest.fixture
    def ranker(self):
        return ContextRanker()

    @pytest.fixture
    def retrieval_plan(self):
        return RetrievalPlan(
            strategy=RetrievalStrategyType.PARALLEL,
            sub_queries=["diabetes symptoms", "diabetes treatment"],
            weights=[1.0, 1.0],
            top_k_per_query=5,
            merge_strategy="score_weighted",
        )

    async def test_rank_with_results(self, ranker, sample_results, retrieval_plan, sample_analysis):
        ranked = await ranker.rank(sample_results, "diabetes query", retrieval_plan, sample_analysis)
        assert len(ranked.chunk_ids) > 0
        assert len(ranked.ranking_scores) == len(ranked.chunk_ids)
        assert ranked.total_original == len(sample_results)
        assert ranked.retained <= ranked.total_original

    async def test_rank_empty_results(self, ranker, retrieval_plan, sample_analysis):
        ranked = await ranker.rank([], "test", retrieval_plan, sample_analysis)
        assert ranked.chunk_ids == []
        assert ranked.total_original == 0
        assert ranked.retained == 0

    async def test_rank_deduplicates_by_knowledge_id(self, ranker, retrieval_plan, sample_analysis):
        class DupResult:
            def __init__(self, cid, kid, content, score):
                self.chunk_id = cid
                self.knowledge_id = kid
                self.content = content
                self.score = score
                self.evidence_text = content
                self.metadata = {"source": "test", "document_id": "doc1"}

        results = [
            DupResult("c1", "k1", "Unique content A", 0.9),
            DupResult("c2", "k1", "Duplicate knowledge_id", 0.85),
            DupResult("c3", "k2", "Unique content B", 0.8),
        ]
        ranked = await ranker.rank(results, "test", retrieval_plan, sample_analysis)
        assert ranked.retained <= 2

    async def test_rank_scores_sorted(self, ranker, sample_results, retrieval_plan, sample_analysis):
        ranked = await ranker.rank(sample_results, "diabetes query", retrieval_plan, sample_analysis)
        if len(ranked.ranking_scores) >= 2:
            for i in range(len(ranked.ranking_scores) - 1):
                assert ranked.ranking_scores[i] >= ranked.ranking_scores[i + 1]

    async def test_rank_diversity_scores(self, ranker, sample_results, retrieval_plan, sample_analysis):
        ranked = await ranker.rank(sample_results, "diabetes query", retrieval_plan, sample_analysis)
        assert len(ranked.diversity_scores) == len(ranked.chunk_ids)
        for ds in ranked.diversity_scores:
            assert 0 <= ds <= 1.0


# ---------------------------------------------------------------------------
# ContextCompressor Tests
# ---------------------------------------------------------------------------

class TestContextCompressor:
    @pytest.fixture
    def compressor(self):
        return ContextCompressor()

    @pytest.fixture
    def ranked_context(self, sample_results):
        return RankedContext(
            chunk_ids=[r.chunk_id for r in sample_results[:3]],
            ranking_scores=[0.92, 0.88, 0.75],
            diversity_scores=[1.0, 0.8, 0.6],
            total_original=5,
            retained=3,
        )

    async def test_compress_no_truncation(self, compressor, sample_results, ranked_context):
        compressed = await compressor.compress(sample_results, ranked_context, "diabetes", 99999)
        assert compressed.context
        assert compressed.compression_ratio == 0.0
        assert compressed.strategy == CompressionStrategy.NONE

    async def test_compress_with_truncation(self, compressor, sample_results, ranked_context):
        compressed = await compressor.compress(sample_results, ranked_context, "diabetes", 10)
        assert compressed.context
        assert compressed.compression_ratio > 0.0
        assert compressed.strategy == CompressionStrategy.EXTRACTIVE

    async def test_compress_empty_results(self, compressor, ranked_context):
        compressed = await compressor.compress([], ranked_context, "test", 4096)
        assert compressed.context == ""
        assert compressed.original_token_count == 0
        assert compressed.compressed_token_count == 0

    async def test_compress_removed_chunks_tracked(self, compressor, sample_results, ranked_context):
        compressed = await compressor.compress(sample_results, ranked_context, "diabetes", 10)
        assert len(compressed.removed_chunk_ids) > 0

    async def test_compress_preserves_ranked_order(self, compressor, sample_results, ranked_context):
        compressed = await compressor.compress(sample_results, ranked_context, "diabetes", 99999)
        assert "[Source 1]" in compressed.context
        assert "[Source 2]" in compressed.context
        assert "[Source 3]" in compressed.context

    async def test_compress_context_contains_content(self, compressor, sample_results, ranked_context):
        compressed = await compressor.compress(sample_results, ranked_context, "diabetes", 99999)
        assert "diabetes" in compressed.context.lower() or "metformin" in compressed.context.lower()


# ---------------------------------------------------------------------------
# PromptAssembler Tests
# ---------------------------------------------------------------------------

class TestPromptAssembler:
    @pytest.fixture
    def assembler(self):
        return PromptAssembler()

    @pytest.fixture
    def compressed_context(self):
        return CompressedContext(
            context="[Source 1]:\nType 2 diabetes is a metabolic disorder.\n\n[Source 2]:\nMetformin is first-line treatment.",
            original_token_count=50,
            compressed_token_count=50,
            compression_ratio=0.0,
            strategy=CompressionStrategy.NONE,
        )

    @pytest.fixture
    def reasoning_plan(self):
        return ReasoningPlan(
            approach=ReasoningApproach.EVIDENCE_SYNTHESIS,
            reasoning_steps=[ReasoningStep(step_number=1, description="Identify key clinical question")],
            target_audience="patient",
            complexity_level="basic",
        )

    @pytest.fixture
    def evidence_plan(self):
        return EvidencePlan(
            evidence_requirements=[EvidenceRequirement(topic="diabetes", priority=EvidencePriority.ESSENTIAL)],
            retrieval_queries=["diabetes treatment"],
        )

    async def test_assemble_basic(self, assembler, sample_analysis, compressed_context, reasoning_plan, evidence_plan):
        prompt = await assembler.assemble("What is diabetes?", compressed_context, reasoning_plan, evidence_plan, sample_analysis)
        assert prompt.system_message
        assert prompt.user_prompt
        assert prompt.token_count > 0
        assert "Medical Query" in prompt.user_prompt or "diabetes" in prompt.user_prompt.lower()

    async def test_assemble_empty_query(self, assembler, compressed_context, reasoning_plan, evidence_plan, sample_analysis):
        with pytest.raises(PromptAssemblyError):
            await assembler.assemble("", compressed_context, reasoning_plan, evidence_plan, sample_analysis)

    async def test_assemble_includes_context(self, assembler, sample_analysis, compressed_context, reasoning_plan, evidence_plan):
        prompt = await assembler.assemble("test", compressed_context, reasoning_plan, evidence_plan, sample_analysis)
        assert "Medical Context" in prompt.system_message

    async def test_assemble_approach_instruction(self, assembler, sample_analysis, compressed_context, evidence_plan):
        for approach in ReasoningApproach:
            rp = ReasoningPlan(approach=approach, target_audience="patient", complexity_level="basic")
            prompt = await assembler.assemble("test", compressed_context, rp, evidence_plan, sample_analysis)
            assert prompt.system_message

    async def test_assemble_prompt_name_and_version(self, assembler, sample_analysis, compressed_context, reasoning_plan, evidence_plan):
        prompt = await assembler.assemble("test", compressed_context, reasoning_plan, evidence_plan, sample_analysis)
        assert prompt.prompt_name == "medical_reasoning"
        assert prompt.prompt_version == "1.0.0"

    async def test_assemble_variables(self, assembler, sample_analysis, compressed_context, reasoning_plan, evidence_plan):
        prompt = await assembler.assemble("test", compressed_context, reasoning_plan, evidence_plan, sample_analysis)
        assert "context" in prompt.variables
        assert "approach" in prompt.variables
        assert "audience" in prompt.variables

    async def test_assemble_specialty_in_user_prompt(self, assembler, sample_analysis, compressed_context, reasoning_plan, evidence_plan):
        prompt = await assembler.assemble("test", compressed_context, reasoning_plan, evidence_plan, sample_analysis)
        assert "Endocrinology" in prompt.user_prompt or "cardiology" in prompt.user_prompt


# ---------------------------------------------------------------------------
# CitationPlanner Tests
# ---------------------------------------------------------------------------

class TestCitationPlanner:
    @pytest.fixture
    def planner(self):
        return CitationPlanner()

    @pytest.fixture
    def ranked_context(self, sample_results):
        return RankedContext(
            chunk_ids=[r.chunk_id for r in sample_results],
            ranking_scores=[0.92, 0.88, 0.75, 0.70, 0.65],
            diversity_scores=[1.0, 0.8, 0.6, 0.4, 0.2],
            total_original=5,
            retained=5,
        )

    async def test_plan_with_results(self, planner, sample_results, ranked_context):
        plan = await planner.plan(sample_results, ranked_context)
        assert len(plan.chunk_ids) > 0
        assert plan.coverage >= 0
        assert len(plan.priority_order) > 0

    async def test_plan_empty_results(self, planner, ranked_context):
        plan = await planner.plan([], ranked_context)
        assert plan.chunk_ids == []
        assert plan.coverage == 0.0

    async def test_plan_citation_map(self, planner, sample_results, ranked_context):
        plan = await planner.plan(sample_results, ranked_context)
        assert len(plan.citation_map) > 0
        for cid, refs in plan.citation_map.items():
            assert len(refs) > 0

    async def test_plan_priority_order_highest_first(self, planner, sample_results, ranked_context):
        plan = await planner.plan(sample_results, ranked_context)
        if len(plan.priority_order) >= 2:
            first_id = plan.priority_order[0]
            assert first_id == sample_results[0].chunk_id


# ---------------------------------------------------------------------------
# ConfidencePlanner Tests
# ---------------------------------------------------------------------------

class TestConfidencePlanner:
    @pytest.fixture
    def planner(self):
        return ConfidencePlanner()

    @pytest.fixture
    def ranked_context(self, sample_results):
        return RankedContext(
            chunk_ids=[r.chunk_id for r in sample_results],
            ranking_scores=[0.92, 0.88, 0.75],
            diversity_scores=[1.0, 0.8, 0.6],
            total_original=5,
            retained=3,
        )

    async def test_plan_with_data(self, planner, sample_results, ranked_context, sample_analysis):
        plan = await planner.plan(sample_results, ranked_context, sample_analysis)
        assert plan.expected_retrieval_confidence > 0
        assert plan.min_expected_confidence >= 0.3
        assert len(plan.confidence_factors) > 0

    async def test_plan_empty_results(self, planner, sample_analysis):
        empty_context = RankedContext()
        plan = await planner.plan([], empty_context, sample_analysis)
        assert plan.expected_retrieval_confidence == 0.0

    async def test_plan_higher_threshold_for_emergency(self, planner, sample_results, ranked_context, emergency_analysis):
        plan = await planner.plan(sample_results, ranked_context, emergency_analysis)
        assert plan.min_expected_confidence >= 0.5

    async def test_plan_confidence_thresholds(self, planner, sample_results, ranked_context, sample_analysis):
        plan = await planner.plan(sample_results, ranked_context, sample_analysis)
        assert "retrieval_confidence" in plan.confidence_thresholds
        assert "evidence_coverage" in plan.confidence_thresholds
        assert "citation_confidence" in plan.confidence_thresholds

    async def test_plan_factors_include_retrieval_info(self, planner, sample_results, ranked_context, sample_analysis):
        plan = await planner.plan(sample_results, ranked_context, sample_analysis)
        factor_text = " ".join(plan.confidence_factors).lower()
        assert "result" in factor_text or "score" in factor_text or "confidence" in factor_text


# ---------------------------------------------------------------------------
# SafetyPlanner Tests
# ---------------------------------------------------------------------------

class TestSafetyPlanner:
    @pytest.fixture
    def planner(self):
        return SafetyPlanner()

    @pytest.fixture
    def reasoning_plan(self):
        return ReasoningPlan(
            approach=ReasoningApproach.EVIDENCE_SYNTHESIS,
            target_audience="patient",
            complexity_level="basic",
        )

    async def test_plan_basic(self, planner, sample_analysis, reasoning_plan):
        plan = await planner.plan("test query", sample_analysis, reasoning_plan)
        assert len(plan.constraints) > 0
        assert len(plan.required_checks) > 0
        assert len(plan.disclaimers) > 0

    async def test_plan_empty_query(self, planner, sample_analysis, reasoning_plan):
        with pytest.raises(SafetyPlanningError):
            await planner.plan("", sample_analysis, reasoning_plan)

    async def test_plan_emergency_disclaimers(self, planner, emergency_analysis, reasoning_plan):
        plan = await planner.plan("chest pain", emergency_analysis, reasoning_plan)
        disclaimer_text = " ".join(plan.disclaimers).lower()
        assert "emergency" in disclaimer_text

    async def test_plan_routine_disclaimers(self, planner, sample_analysis, reasoning_plan):
        plan = await planner.plan("test", sample_analysis, reasoning_plan)
        disclaimer_text = " ".join(plan.disclaimers).lower()
        assert "educational" in disclaimer_text or "advice" in disclaimer_text

    async def test_plan_constraints_for_patient_audience(self, planner, sample_analysis, reasoning_plan):
        plan = await planner.plan("test", sample_analysis, reasoning_plan)
        constraint_text = " ".join(plan.constraints).lower()
        assert "plain language" in constraint_text or "consult" in constraint_text

    async def test_plan_constraints_for_doctor_audience(self, planner, reasoning_plan):
        doctor_analysis = QueryUnderstandingResult(
            original_query="test",
            audience=AudienceResult(audience=AudienceType.DOCTOR, confidence=0.9),
            language=LanguageInfo(language="en"),
            analysis_scope="full",
        )
        plan = await planner.plan("test", doctor_analysis, reasoning_plan)
        constraint_text = " ".join(plan.constraints).lower()
        assert "clinical terminology" in constraint_text or "evidence" in constraint_text

    async def test_plan_dangerous_topic_detection(self, planner, sample_analysis, reasoning_plan):
        plan = await planner.plan("I want to commit suicide", sample_analysis, reasoning_plan)
        assert len(plan.prohibited_content_patterns) > 0
        assert "suicide" in plan.prohibited_content_patterns

    async def test_plan_required_checks_emergency(self, planner, emergency_analysis, reasoning_plan):
        plan = await planner.plan("chest pain", emergency_analysis, reasoning_plan)
        check_text = " ".join(plan.required_checks)
        assert "validate_emergency_response" in check_text


# ---------------------------------------------------------------------------
# ReasoningPipeline Tests
# ---------------------------------------------------------------------------

class TestReasoningPipeline:
    @pytest.fixture
    def pipeline(self):
        return ReasoningPipeline()

    async def test_pipeline_run_full(self, pipeline, sample_analysis):
        result = await pipeline.run(
            query="What are the symptoms and treatment for type 2 diabetes?",
            analysis=sample_analysis,
            top_k=10,
        )
        assert "reasoning_plan" in result
        assert "evidence_plan" in result
        assert "retrieval_plan" in result
        assert "ranked_context" in result
        assert "compressed_context" in result
        assert "assembled_prompt" in result
        assert "citation_plan" in result
        assert "confidence_plan" in result
        assert "safety_plan" in result
        assert "stages" in result
        assert "total_time_ms" in result

    async def test_pipeline_run_without_analysis(self, pipeline):
        result = await pipeline.run(
            query="What is diabetes?",
            top_k=5,
        )
        assert "analysis" in result
        assert "reasoning_plan" in result

    async def test_pipeline_approach_hint(self, pipeline, sample_analysis):
        result = await pipeline.run(
            query="test",
            analysis=sample_analysis,
            approach_hint="clinical_reasoning",
        )
        plan: ReasoningPlan = result["reasoning_plan"]
        assert plan.approach == ReasoningApproach.CLINICAL_REASONING

    async def test_pipeline_stages_all_present(self, pipeline, sample_analysis):
        result = await pipeline.run(query="test", analysis=sample_analysis)
        expected_stages = [
            "reasoning_plan", "evidence_plan", "retrieval_strategy",
            "context_ranking", "context_compression", "prompt_assembly",
            "citation_planning", "confidence_planning", "safety_planning",
        ]
        for stage in expected_stages:
            assert stage in result["stages"], f"Missing stage: {stage}"

    async def test_pipeline_handles_analysis_stage_timing(self, pipeline):
        result = await pipeline.run(query="What is diabetes?", top_k=5)
        assert "analysis" in result["stages"]
        assert result["stages"]["analysis"] > 0


# ---------------------------------------------------------------------------
# ReasoningService Tests
# ---------------------------------------------------------------------------

class TestReasoningService:
    @pytest.fixture
    def service(self):
        return ReasoningService()

    async def test_reason_basic(self, service):
        response = await service.reason(
            query="What are the symptoms of diabetes?",
            top_k=5,
        )
        assert isinstance(response, ReasoningResponse)
        assert response.request.original_query == "What are the symptoms of diabetes?"
        assert response.reasoning_plan is not None
        assert response.evidence_plan is not None
        assert response.retrieval_plan is not None
        assert response.ranked_context is not None
        assert response.compressed_context is not None
        assert response.assembled_prompt is not None
        assert response.citation_plan is not None
        assert response.confidence_plan is not None
        assert response.safety_plan is not None
        assert response.processing_time_ms > 0

    async def test_reason_empty_query(self, service):
        with pytest.raises(ReasoningServiceError):
            await service.reason(query="")

    async def test_reason_partial_inclusion(self, service):
        response = await service.reason(
            query="diabetes",
            include_reasoning_plan=True,
            include_evidence_plan=True,
            include_retrieval_plan=False,
            include_context_ranking=False,
            include_context_compression=False,
            include_prompt_assembly=False,
            include_citation_plan=False,
            include_confidence_plan=False,
            include_safety_plan=False,
        )
        assert response.reasoning_plan is not None
        assert response.evidence_plan is not None
        assert response.retrieval_plan is None
        assert response.ranked_context is None
        assert response.assembled_prompt is None

    async def test_reason_all_stages_disabled(self, service):
        response = await service.reason(
            query="diabetes",
            include_reasoning_plan=False,
            include_evidence_plan=False,
            include_retrieval_plan=False,
            include_context_ranking=False,
            include_context_compression=False,
            include_prompt_assembly=False,
            include_citation_plan=False,
            include_confidence_plan=False,
            include_safety_plan=False,
        )
        assert response.reasoning_plan is None
        assert response.evidence_plan is None
        assert response.assembled_prompt is None
        assert response.processing_time_ms > 0

    async def test_reason_approach_hint(self, service):
        response = await service.reason(
            query="What is the treatment for hypertension?",
            approach_hint="clinical_reasoning",
        )
        assert response.reasoning_plan is not None
        assert response.reasoning_plan.approach == ReasoningApproach.CLINICAL_REASONING

    async def test_reason_filters(self, service):
        response = await service.reason(
            query="diabetes",
            filters={"specialty": "endocrinology"},
        )
        assert response.retrieval_plan is not None

    async def test_reason_conversation_id(self, service):
        response = await service.reason(
            query="diabetes",
            conversation_id="conv_123",
        )
        assert response.request.conversation_id == "conv_123"


# ---------------------------------------------------------------------------
# Schemas Tests
# ---------------------------------------------------------------------------

class TestReasoningSchemas:
    def test_reasoning_approach_enum_values(self):
        assert ReasoningApproach.CLINICAL_REASONING.value == "clinical_reasoning"
        assert ReasoningApproach.EVIDENCE_SYNTHESIS.value == "evidence_synthesis"
        assert len(ReasoningApproach) == 8

    def test_retrieval_strategy_type_enum_values(self):
        assert RetrievalStrategyType.SINGLE.value == "single"
        assert RetrievalStrategyType.PARALLEL.value == "parallel"

    def test_compression_strategy_enum_values(self):
        assert CompressionStrategy.NONE.value == "none"
        assert CompressionStrategy.EXTRACTIVE.value == "extractive"

    def test_evidence_priority_enum_values(self):
        assert EvidencePriority.ESSENTIAL.value == "essential"
        assert EvidencePriority.HIGH.value == "high"

    def test_reasoning_step_defaults(self):
        step = ReasoningStep(step_number=1, description="Test step")
        assert step.status == "pending"
        assert step.details == {}

    def test_evidence_requirement_defaults(self):
        req = EvidenceRequirement(topic="test")
        assert req.priority == EvidencePriority.MEDIUM
        assert req.min_results == 1
        assert not req.required

    def test_reasoning_plan_defaults(self):
        plan = ReasoningPlan()
        assert plan.approach == ReasoningApproach.EVIDENCE_SYNTHESIS
        assert plan.target_audience == "patient"
        assert plan.complexity_level == "intermediate"

    def test_evidence_plan_defaults(self):
        plan = EvidencePlan()
        assert plan.min_evidence_count == 3
        assert plan.max_evidence_count == 20

    def test_retrieval_plan_defaults(self):
        plan = RetrievalPlan()
        assert plan.strategy == RetrievalStrategyType.SINGLE
        assert plan.merge_strategy == "score_weighted"

    def test_ranked_context_defaults(self):
        rc = RankedContext()
        assert rc.chunk_ids == []
        assert rc.total_original == 0
        assert rc.retained == 0

    def test_compressed_context_defaults(self):
        cc = CompressedContext()
        assert cc.context == ""
        assert cc.strategy == CompressionStrategy.NONE

    def test_assembled_prompt_defaults(self):
        ap = AssembledPrompt()
        assert ap.system_message == ""
        assert ap.prompt_name == ""

    def test_citation_plan_defaults(self):
        cp = CitationPlan()
        assert cp.chunk_ids == []
        assert cp.coverage == 0.0

    def test_confidence_plan_defaults(self):
        cp = ConfidencePlan()
        assert cp.min_expected_confidence == 0.3
        assert cp.confidence_factors == []

    def test_safety_plan_defaults(self):
        sp = SafetyPlan()
        assert sp.constraints == []

    def test_reasoning_request_defaults(self):
        rr = ReasoningRequest(original_query="test")
        assert rr.top_k == 15
        assert rr.max_context_tokens == 4096
        assert rr.include_reasoning_plan
        assert rr.include_safety_plan

    def test_reasoning_response_fields(self):
        rr = ReasoningResponse(
            request=ReasoningRequest(original_query="test"),
            processing_time_ms=100.0,
            stages={"reasoning": 50.0},
        )
        assert rr.processing_time_ms == 100.0
        assert rr.stages == {"reasoning": 50.0}


# ---------------------------------------------------------------------------
# ReasoningSettings Tests
# ---------------------------------------------------------------------------

class TestReasoningSettings:
    def test_defaults(self):
        settings = ReasoningSettings()
        assert settings.REASONING_ENABLED
        assert settings.REASONING_DEFAULT_APPROACH == "evidence_synthesis"
        assert settings.REASONING_DIVERSITY_WEIGHT == 0.3

    def test_supported_approaches(self):
        settings = ReasoningSettings()
        approaches = settings.supported_approaches
        assert "clinical_reasoning" in approaches
        assert "evidence_synthesis" in approaches
        assert len(approaches) == 8

    def test_compression_strategies(self):
        settings = ReasoningSettings()
        assert "none" in settings.compression_strategies
        assert "extractive" in settings.compression_strategies

    def test_merge_strategies(self):
        settings = ReasoningSettings()
        assert "score_weighted" in settings.merge_strategies
        assert "round_robin" in settings.merge_strategies
