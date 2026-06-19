import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.ai.medical.response.builder.builder import StructuredResponseBuilder
from app.ai.medical.response.config.config import ResponseSettings
from app.ai.medical.response.exceptions.exceptions import (
    PromptCompositionError,
    ResponseBuilderError,
    ResponseOrchestrationError,
    ResponsePipelineError,
    ResponseServiceError,
    ResponseGenerationError,
    StreamingError,
    StructuredResponseError,
)
from app.ai.medical.response.orchestrator.orchestrator import ResponseOrchestrator
from app.ai.medical.response.pipelines.pipelines import ResponsePipeline
from app.ai.medical.response.prompts.composition import PromptCompositionEngine
from app.ai.medical.response.schemas.schemas import (
    Citation,
    ClinicalSection,
    ClinicalSectionType,
    GenerateRequest,
    GenerateResponse,
    GenerateRequestSimple,
    ResponseMetadata,
    StreamChunk,
    StructuredAnswer,
)
from app.ai.medical.response.services.services import ResponseService
from app.ai.medical.response.streaming.streaming import StreamingHandler
from app.ai.medical.response.utils.utils import (
    estimate_tokens,
    extract_sentences,
    merge_content,
    strip_markdown_formatting,
    truncate_text,
)
from app.ai.medical.reasoning.schemas.schemas import ReasoningApproach, ReasoningPlan, ReasoningStep


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_ai_response() -> str:
    return """## Summary
Type 2 diabetes is a chronic metabolic disorder characterized by insulin resistance and relative insulin deficiency.

## Symptoms
Common symptoms include polyuria, polydipsia, weight loss, and fatigue. Many patients may be asymptomatic initially.

## Treatment
First-line treatment includes metformin monotherapy along with lifestyle modifications. HbA1c targets are less than 7.0% for most adults.

## Key Findings
- **Insulin resistance is the primary pathophysiological defect**
- **Metformin remains the first-line pharmacotherapy**
- **Lifestyle modification is essential for disease management**

## Limitations
This information is for educational purposes only; further research may be needed for specific cases."""


@pytest.fixture
def reasoning_plan() -> ReasoningPlan:
    return ReasoningPlan(
        approach=ReasoningApproach.EVIDENCE_SYNTHESIS,
        reasoning_steps=[
            ReasoningStep(step_number=1, description="Identify key clinical question"),
            ReasoningStep(step_number=2, description="Review evidence"),
        ],
        required_evidence_types=["clinical_guidelines"],
        target_audience="patient",
        complexity_level="basic",
        disclaimer="This information is for educational purposes only.",
    )


# ---------------------------------------------------------------------------
# ResponseSettings Tests
# ---------------------------------------------------------------------------

class TestResponseSettings:
    def test_defaults(self):
        settings = ResponseSettings()
        assert settings.RESPONSE_ENABLED
        assert settings.RESPONSE_DEFAULT_TEMPERATURE == 0.7
        assert settings.RESPONSE_DEFAULT_MAX_TOKENS == 2048
        assert settings.RESPONSE_STREAMING_ENABLED
        assert settings.RESPONSE_DISCLAIMER_ENABLED
        assert settings.RESPONSE_FALLBACK_ON_ERROR
        assert settings.RESPONSE_MAX_SECTIONS == 10

    def test_disclaimer_text_default(self):
        settings = ResponseSettings()
        assert "educational purposes" in settings.RESPONSE_DISCLAIMER_TEXT
        assert "medical advice" in settings.RESPONSE_DISCLAIMER_TEXT

    def test_emergency_disclaimer(self):
        settings = ResponseSettings()
        assert "EMERGENCY" in settings.RESPONSE_EMERGENCY_DISCLAIMER
        assert "emergency services" in settings.RESPONSE_EMERGENCY_DISCLAIMER


# ---------------------------------------------------------------------------
# Schemas Tests
# ---------------------------------------------------------------------------

class TestSchemas:
    def test_clinical_section_type_values(self):
        assert ClinicalSectionType.SUMMARY.value == "summary"
        assert ClinicalSectionType.TREATMENT_OPTIONS.value == "treatment_options"
        assert ClinicalSectionType.EMERGENCY_GUIDANCE.value == "emergency_guidance"
        assert len(ClinicalSectionType) == 17

    def test_clinical_section_defaults(self):
        section = ClinicalSection(section_type=ClinicalSectionType.SUMMARY, title="Test", content="Content")
        assert section.priority == 0
        assert section.citations == []
        assert section.disclaimer is None

    def test_structured_answer_defaults(self):
        answer = StructuredAnswer()
        assert answer.summary == ""
        assert answer.sections == []
        assert answer.key_findings == []
        assert answer.formatted_text == ""

    def test_citation_defaults(self):
        citation = Citation(source="Test")
        assert citation.relevance_score == 0.0
        assert citation.evidence_text is None
        assert citation.reference_number == 0

    def test_response_metadata_defaults(self):
        meta = ResponseMetadata()
        assert meta.model == ""
        assert meta.provider == ""
        assert not meta.streaming
        assert not meta.cached

    def test_generate_request_defaults(self):
        req = GenerateRequest(query="test")
        assert req.top_k == 15
        assert req.max_context_tokens == 4096
        assert not req.stream
        assert req.approach_hint is None

    def test_generate_response_fields(self):
        resp = GenerateResponse(query="test", answer="answer")
        assert resp.query == "test"
        assert resp.answer == "answer"
        assert resp.citations == []
        assert resp.key_findings == []
        assert resp.metadata is None

    def test_stream_chunk_defaults(self):
        chunk = StreamChunk(content="hello")
        assert chunk.content == "hello"
        assert not chunk.done
        assert chunk.chunk_index == 0

    def test_generate_request_simple_defaults(self):
        req = GenerateRequestSimple(query="test")
        assert req.top_k == 10
        assert not req.stream


# ---------------------------------------------------------------------------
# PromptCompositionEngine Tests
# ---------------------------------------------------------------------------

class TestPromptCompositionEngine:
    @pytest.fixture
    def engine(self):
        return PromptCompositionEngine()

    async def test_compose_with_query_only(self, engine):
        result = await engine.compose(query="What is diabetes?")
        assert "gateway_request" in result
        assert "messages" in result
        assert len(result["messages"]) == 1
        assert result["messages"][0]["role"] == "user"

    async def test_compose_empty_query(self, engine):
        with pytest.raises(PromptCompositionError):
            await engine.compose(query="")

    async def test_compose_with_assembled_prompt(self, engine):
        assembled = {
            "system_message": "You are a medical assistant.",
            "user_prompt": "What is diabetes?",
        }
        result = await engine.compose(query="test", assembled_prompt=assembled)
        assert len(result["messages"]) == 2
        assert result["messages"][0]["role"] == "system"
        assert result["messages"][1]["role"] == "user"

    async def test_compose_with_reasoning_plan_disclaimer(self, engine, reasoning_plan):
        result = await engine.compose(query="test", reasoning_plan=reasoning_plan)
        assert "Note:" in result["messages"][0]["content"]

    async def test_compose_temperature_and_max_tokens(self, engine):
        result = await engine.compose(query="test", temperature=0.5, max_tokens=100)
        assert result["temperature"] == 0.5
        assert result["max_tokens"] == 100

    async def test_compose_with_conversation_id(self, engine):
        result = await engine.compose(query="test", conversation_id="conv_1")
        assert result["gateway_request"].conversation_id == "conv_1"


# ---------------------------------------------------------------------------
# StructuredResponseBuilder Tests
# ---------------------------------------------------------------------------

class TestStructuredResponseBuilder:
    @pytest.fixture
    def builder(self):
        return StructuredResponseBuilder()

    async def test_build_with_content(self, builder, sample_ai_response):
        response = await builder.build(raw_content=sample_ai_response, query="diabetes")
        assert response.answer
        assert response.query == "diabetes"
        assert len(response.sections) > 0
        assert response.structured_answer is not None

    async def test_build_empty_content(self, builder):
        with pytest.raises(StructuredResponseError):
            await builder.build(raw_content="")

    async def test_build_sections_parsed(self, builder, sample_ai_response):
        response = await builder.build(raw_content=sample_ai_response)
        assert len(response.sections) >= 3
        section_types = [s.section_type for s in response.sections]
        assert ClinicalSectionType.SUMMARY in section_types

    async def test_build_extracts_citations(self, builder):
        content = "Some text [Source 1] and [Source 2] with references."
        response = await builder.build(raw_content=content)
        assert len(response.citations) >= 1

    async def test_build_extracts_key_findings(self, builder, sample_ai_response):
        response = await builder.build(raw_content=sample_ai_response)
        assert len(response.key_findings) > 0

    async def test_build_disclaimer_included(self, builder, sample_ai_response, reasoning_plan):
        response = await builder.build(
            raw_content=sample_ai_response,
            reasoning_plan=reasoning_plan,
        )
        assert response.disclaimer

    async def test_build_fallback_for_no_sections(self, builder):
        response = await builder.build(raw_content="Simple response without headers.")
        assert len(response.sections) >= 1

    async def test_build_limitations_extracted(self, builder, sample_ai_response):
        response = await builder.build(raw_content=sample_ai_response)
        assert len(response.limitations) > 0

    async def test_build_section_classification(self, builder):
        content = """## Emergency Guidance
If you experience chest pain, call emergency services immediately.

## Risk Factors
Common risk factors include smoking, obesity, and family history."""
        response = await builder.build(raw_content=content)
        section_types = [s.section_type for s in response.sections]
        assert ClinicalSectionType.EMERGENCY_GUIDANCE in section_types
        assert ClinicalSectionType.RISK_FACTORS in section_types

    async def test_build_with_reasoning_plan(self, builder, sample_ai_response, reasoning_plan):
        response = await builder.build(
            raw_content=sample_ai_response,
            reasoning_plan=reasoning_plan,
            query="diabetes",
            conversation_id="conv_1",
        )
        assert response.conversation_id == "conv_1"

    async def test_build_formatted_text(self, builder, sample_ai_response):
        response = await builder.build(raw_content=sample_ai_response)
        assert response.structured_answer.formatted_text
        assert "## Summary" in response.structured_answer.formatted_text


# ---------------------------------------------------------------------------
# ResponseOrchestrator Tests
# ---------------------------------------------------------------------------

class TestResponseOrchestrator:
    @pytest.fixture
    def orchestrator(self):
        return ResponseOrchestrator()

    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.execute_gateway")
    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.compose")
    async def test_generate_basic(self, mock_compose, mock_execute, orchestrator, sample_ai_response):
        mock_compose.return_value = {
            "gateway_request": MagicMock(),
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        mock_execute.return_value = {
            "content": sample_ai_response,
            "model": "test-model",
            "provider": "test-provider",
            "usage": {"prompt_tokens": 50, "completion_tokens": 100},
            "finish_reason": "stop",
        }

        request = GenerateRequest(query="What is diabetes?")
        response = await orchestrator.generate(request)
        assert response.answer
        assert len(response.sections) > 0

    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.execute_gateway")
    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.compose")
    async def test_generate_with_reasoning_plan(
        self, mock_compose, mock_execute, orchestrator, sample_ai_response, reasoning_plan
    ):
        mock_compose.return_value = {
            "gateway_request": MagicMock(),
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        mock_execute.return_value = {
            "content": sample_ai_response,
            "model": "test-model",
            "provider": "test-provider",
            "usage": {},
            "finish_reason": "stop",
        }

        request = GenerateRequest(
            query="What is diabetes?",
            reasoning_plan=reasoning_plan.model_dump(),
        )
        response = await orchestrator.generate(request)
        assert response.metadata is not None

    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.compose")
    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.execute_gateway")
    async def test_generate_fallback_on_error(self, mock_execute, mock_compose, orchestrator, sample_ai_response):
        mock_compose.return_value = {
            "gateway_request": MagicMock(),
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        mock_execute.side_effect = Exception("Gateway error")

        request = GenerateRequest(query="test")
        response = await orchestrator.generate(request)
        assert "unable to generate" in response.answer.lower()

    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.compose")
    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.execute_gateway")
    async def test_generate_no_fallback(self, mock_execute, mock_compose):
        settings = ResponseSettings(RESPONSE_FALLBACK_ON_ERROR=False)
        orchestrator = ResponseOrchestrator(settings=settings)
        mock_compose.return_value = {
            "gateway_request": MagicMock(),
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        mock_execute.side_effect = Exception("Gateway error")

        request = GenerateRequest(query="test")
        with pytest.raises(ResponseOrchestrationError):
            await orchestrator.generate(request)

    async def test_generate_invalid_reasoning_plan(self, orchestrator, sample_ai_response):
        request = GenerateRequest(
            query="test",
            reasoning_plan={"invalid": "data"},
        )
        with patch.object(
            orchestrator._prompt_engine, "compose",
            new=AsyncMock(return_value={
                "gateway_request": MagicMock(),
                "messages": [{"role": "user", "content": "test"}],
                "temperature": 0.7,
                "max_tokens": 2048,
            }),
        ):
            with patch.object(
                orchestrator._prompt_engine, "execute_gateway",
                new=AsyncMock(return_value={
                    "content": sample_ai_response,
                    "model": "test",
                    "provider": "test",
                    "usage": {},
                    "finish_reason": "stop",
                }),
            ):
                response = await orchestrator.generate(request)
                assert response.answer


# ---------------------------------------------------------------------------
# ResponsePipeline Tests
# ---------------------------------------------------------------------------

class TestResponsePipeline:
    @pytest.fixture
    def pipeline(self):
        return ResponsePipeline()

    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.execute_gateway")
    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.compose")
    async def test_run_basic(self, mock_compose, mock_execute, pipeline, sample_ai_response):
        mock_compose.return_value = {
            "gateway_request": MagicMock(),
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        mock_execute.return_value = {
            "content": sample_ai_response,
            "model": "test-model",
            "provider": "test-provider",
            "usage": {},
            "finish_reason": "stop",
        }

        request = GenerateRequest(query="What is diabetes?")
        response = await pipeline.run(request)
        assert response.answer
        assert response.processing_time_ms > 0

    async def test_run_empty_query(self, pipeline):
        request = GenerateRequest.model_construct(query="", _fields_set={"query"})
        with pytest.raises((ResponsePipelineError, Exception)):
            await pipeline.run(request)

    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.execute_gateway")
    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.compose")
    async def test_run_fallback_on_error(self, mock_compose, mock_execute, pipeline):
        mock_compose.side_effect = Exception("error")

        request = GenerateRequest(query="test")
        response = await pipeline.run(request)
        assert "unable to generate" in response.answer.lower()

    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.compose")
    async def test_run_no_fallback(self, mock_compose):
        settings = ResponseSettings(RESPONSE_FALLBACK_ON_ERROR=False)
        pipeline = ResponsePipeline(settings=settings)
        mock_compose.side_effect = Exception("error")

        request = GenerateRequest(query="test")
        with pytest.raises(ResponsePipelineError):
            await pipeline.run(request)


# ---------------------------------------------------------------------------
# ResponseService Tests
# ---------------------------------------------------------------------------

class TestResponseService:
    @pytest.fixture
    def service(self):
        return ResponseService()

    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.execute_gateway")
    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.compose")
    async def test_generate_basic(self, mock_compose, mock_execute, service, sample_ai_response):
        mock_compose.return_value = {
            "gateway_request": MagicMock(),
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        mock_execute.return_value = {
            "content": sample_ai_response,
            "model": "test-model",
            "provider": "test-provider",
            "usage": {},
            "finish_reason": "stop",
        }

        request = GenerateRequest(query="What is diabetes?")
        response = await service.generate(request)
        assert response.answer

    async def test_generate_empty_query(self, service):
        request = GenerateRequest.model_construct(query="", _fields_set={"query"})
        with pytest.raises((ResponseServiceError, Exception)):
            await service.generate(request)

    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.compose")
    async def test_generate_fallback_on_error(self, mock_compose, service):
        mock_compose.side_effect = Exception("error")
        request = GenerateRequest(query="test")
        response = await service.generate(request)
        assert response.answer

    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.compose")
    @patch("app.ai.medical.response.prompts.composition.PromptCompositionEngine.execute_gateway")
    async def test_generate_no_fallback(self, mock_execute, mock_compose):
        settings = ResponseSettings(RESPONSE_FALLBACK_ON_ERROR=False)
        service = ResponseService(settings=settings)
        mock_compose.return_value = {
            "gateway_request": MagicMock(),
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.7,
            "max_tokens": 2048,
        }
        mock_execute.side_effect = Exception("error")
        request = GenerateRequest(query="test")
        with pytest.raises(ResponseServiceError):
            await service.generate(request)


# ---------------------------------------------------------------------------
# StreamingHandler Tests
# ---------------------------------------------------------------------------

class TestStreamingHandler:
    @pytest.fixture
    def handler(self):
        return StreamingHandler(chunk_size=50)

    async def test_stream_text_basic(self, handler):
        text = "Type 2 diabetes is a chronic metabolic disorder."
        chunks = []
        async for chunk in handler.stream_text(text):
            chunks.append(chunk)
        assert len(chunks) >= 2
        assert chunks[-1].done

    async def test_stream_text_empty(self, handler):
        chunks = []
        async for chunk in handler.stream_text(""):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0].done

    async def test_stream_text_small(self, handler):
        chunks = []
        async for chunk in handler.stream_text("Hello"):
            chunks.append(chunk)
        assert len(chunks) >= 1

    async def test_chunk_size_validation(self):
        with pytest.raises(StreamingError):
            StreamingHandler(chunk_size=0)

    async def test_stream_text_chunk_indices(self, handler):
        chunks = []
        async for chunk in handler.stream_text("a b c d e f g h i j k l m n o p"):
            chunks.append(chunk)
        non_done = [c for c in chunks if not c.done]
        for i, chunk in enumerate(non_done):
            assert chunk.chunk_index >= 0

    async def test_stream_sections(self, handler):
        sections = [("Summary", "Diabetes overview content"), ("Treatment", "Metformin is first line")]
        chunks = []
        async for chunk in handler.stream_sections(sections):
            chunks.append(chunk)
        assert len(chunks) >= 2
        assert chunks[-1].done

    async def test_estimate_chunks(self, handler):
        text = "word " * 100
        estimate = handler.estimate_chunks(text)
        assert estimate >= 1


# ---------------------------------------------------------------------------
# Utils Tests
# ---------------------------------------------------------------------------

class TestUtils:
    def test_estimate_tokens(self):
        assert estimate_tokens("") == 0
        len_hello = len("Hello world") // 4
        assert estimate_tokens("Hello world") == max(1, len_hello)
        assert estimate_tokens("a" * 100) == 25

    def test_truncate_text(self):
        assert truncate_text("") == ""
        assert truncate_text("Hello", 100) == "Hello"
        result = truncate_text("Hello World", 5)
        assert "[truncated]" in result
        assert len(result) <= 20

    def test_strip_markdown_formatting(self):
        result = strip_markdown_formatting("**bold** and *italic* and `code`")
        assert "**" not in result
        assert "*" not in result
        assert "bold" in result
        assert "italic" in result
        assert "code" in result

    def test_extract_sentences(self):
        text = "First sentence. Second sentence! Third sentence? Fourth."
        result = extract_sentences(text)
        assert len(result) == 4

    def test_extract_sentences_empty(self):
        assert extract_sentences("") == []

    def test_extract_sentences_max(self):
        text = "One. Two. Three. Four. Five. Six. Seven."
        result = extract_sentences(text, max_sentences=3)
        assert len(result) == 3

    def test_merge_content(self):
        assert merge_content("", "new") == "new"
        assert merge_content("old", "") == "old"
        result = merge_content("First", "Second")
        assert "First" in result
        assert "Second" in result


# ---------------------------------------------------------------------------
# Builder Edge Cases Tests
# ---------------------------------------------------------------------------

class TestBuilderEdgeCases:
    @pytest.fixture
    def builder(self):
        return StructuredResponseBuilder()

    async def test_build_no_headers(self, builder):
        response = await builder.build(raw_content="Plain text without any markdown headers.")
        assert response.answer
        assert len(response.sections) >= 1

    async def test_build_only_asterisk_headers(self, builder):
        content = "**Summary**\nThis is the summary.\n\n**Details**\nThese are the details."
        response = await builder.build(raw_content=content)
        assert len(response.sections) >= 1

    async def test_build_long_content_trimming(self, builder):
        long_content = "## Summary\n" + "A" * 5000
        response = await builder.build(raw_content=long_content)
        assert len(response.sections) <= 10

    async def test_build_section_classification_all_types(self, builder):
        for section_type in ClinicalSectionType:
            keyword = None
            for st, keywords in [
                (ClinicalSectionType.SUMMARY, ["Summary"]),
                (ClinicalSectionType.SYMPTOM_ANALYSIS, ["Symptoms"]),
                (ClinicalSectionType.DIFFERENTIAL_DIAGNOSIS, ["Differential Diagnosis"]),
                (ClinicalSectionType.DIAGNOSTIC_APPROACH, ["Diagnostic"]),
                (ClinicalSectionType.TREATMENT_OPTIONS, ["Treatment"]),
                (ClinicalSectionType.MEDICATION_INFO, ["Medication"]),
                (ClinicalSectionType.RISK_FACTORS, ["Risk Factors"]),
                (ClinicalSectionType.EMERGENCY_GUIDANCE, ["Emergency"]),
                (ClinicalSectionType.GENERAL_INFO, ["General Information"]),
            ]:
                if st == section_type:
                    keyword = keywords[0]
                    break

            if keyword:
                content = f"## {keyword}\nTest content for {keyword}."
                response = await builder.build(raw_content=content)
                types_found = [s.section_type for s in response.sections]
                assert section_type in types_found, f"Failed to classify {section_type} from keyword '{keyword}'"


# ---------------------------------------------------------------------------
# Citation Extraction Tests
# ---------------------------------------------------------------------------

class TestCitationExtraction:
    @pytest.fixture
    def builder(self):
        return StructuredResponseBuilder()

    async def test_citation_source_pattern(self, builder):
        content = "Evidence shows [Source 1] and [Source 2] are relevant."
        response = await builder.build(raw_content=content)
        assert len(response.citations) >= 2

    async def test_citation_bracket_pattern(self, builder):
        content = "According to [1] and [2], the evidence supports."
        response = await builder.build(raw_content=content)
        assert len(response.citations) >= 1

    async def test_citation_deduplication(self, builder):
        content = "See [Source 1] and also [Source 1] again."
        response = await builder.build(raw_content=content)
        assert len(response.citations) == 1

    async def test_citations_empty(self, builder):
        content = "No citations in this text at all."
        response = await builder.build(raw_content=content)
        assert response.citations == []


# ---------------------------------------------------------------------------
# ClinicalSection Classification Tests
# ---------------------------------------------------------------------------

class TestSectionClassification:
    @pytest.fixture
    def builder(self):
        return StructuredResponseBuilder()

    def test_classify_summary(self, builder):
        assert builder._classify_section("Summary") == ClinicalSectionType.SUMMARY
        assert builder._classify_section("Overview") == ClinicalSectionType.SUMMARY
        assert builder._classify_section("Key Points") == ClinicalSectionType.SUMMARY

    def test_classify_symptoms(self, builder):
        assert builder._classify_section("Symptoms") == ClinicalSectionType.SYMPTOM_ANALYSIS
        assert builder._classify_section("Clinical Presentation") == ClinicalSectionType.SYMPTOM_ANALYSIS

    def test_classify_treatment(self, builder):
        assert builder._classify_section("Treatment Options") == ClinicalSectionType.TREATMENT_OPTIONS
        assert builder._classify_section("Management") == ClinicalSectionType.TREATMENT_OPTIONS

    def test_classify_emergency(self, builder):
        for header in ("Emergency Guidance", "Urgent Care", "Call Emergency"):
            assert builder._classify_section(header) == ClinicalSectionType.EMERGENCY_GUIDANCE, f"Failed: {header}"

    def test_classify_general(self, builder):
        assert builder._classify_section("Random Section") == ClinicalSectionType.GENERAL_INFO


# ---------------------------------------------------------------------------
# StreamingHandler Edge Cases Tests
# ---------------------------------------------------------------------------

class TestStreamingEdgeCases:
    async def test_stream_single_char_chunks(self):
        handler = StreamingHandler(chunk_size=1)
        text = "ab cd"
        chunks = []
        async for chunk in handler.stream_text(text):
            chunks.append(chunk)
        done_chunks = [c for c in chunks if c.done]
        content_chunks = [c for c in chunks if not c.done and c.content.strip()]
        assert len(content_chunks) > 0
        assert len(done_chunks) == 1

    async def test_stream_large_chunk_size(self):
        handler = StreamingHandler(chunk_size=10000)
        text = "Short text"
        chunks = []
        async for chunk in handler.stream_text(text):
            chunks.append(chunk)
        assert len(chunks) == 2

    async def test_stream_sections_empty(self):
        handler = StreamingHandler()
        chunks = []
        async for chunk in handler.stream_sections([]):
            chunks.append(chunk)
        assert len(chunks) == 1
        assert chunks[0].done


# ---------------------------------------------------------------------------
# ResponseGenerationError Tests
# ---------------------------------------------------------------------------

class TestExceptions:
    def test_exception_hierarchy(self):
        assert issubclass(PromptCompositionError, ResponseGenerationError)
        assert issubclass(ResponseBuilderError, ResponseGenerationError)
        assert issubclass(ResponseOrchestrationError, ResponseGenerationError)
        assert issubclass(ResponsePipelineError, ResponseGenerationError)
        assert issubclass(ResponseServiceError, ResponseGenerationError)
        assert issubclass(StreamingError, ResponseGenerationError)

    def test_exception_message(self):
        try:
            raise ResponseServiceError("Test error message")
        except ResponseServiceError as e:
            assert "Test error message" in str(e)
