import asyncio
import time
from datetime import datetime

from app.ai.evidence.config import EvidenceConfig
from app.ai.evidence.engines.citation import CitationFormatterEngine, CitationGeneratorEngine
from app.ai.evidence.engines.confidence import ConfidenceCalculatorEngine
from app.ai.evidence.engines.conflict import ConflictDetectorEngine
from app.ai.evidence.engines.coverage import CoverageAnalyzerEngine
from app.ai.evidence.engines.explain import ExplainabilityProviderEngine
from app.ai.evidence.engines.provenance import ProvenanceTrackerEngine
from app.ai.evidence.engines.ranking import SourceRankingEngine
from app.ai.evidence.engines.verifier import EvidenceVerifierEngine
from app.ai.evidence.exceptions import EvidencePipelineError
from app.ai.evidence.schemas import (
    CitationStyle,
    EvidenceSpan,
    EvidenceState,
    PipelineResult,
    ProvenanceAction,
    ProvenanceEntry,
)


class EvidencePipeline:
    def __init__(
        self,
        verifier: EvidenceVerifierEngine | None = None,
        citation_generator: CitationGeneratorEngine | None = None,
        citation_formatter: CitationFormatterEngine | None = None,
        coverage_analyzer: CoverageAnalyzerEngine | None = None,
        source_ranker: SourceRankingEngine | None = None,
        conflict_detector: ConflictDetectorEngine | None = None,
        confidence_calculator: ConfidenceCalculatorEngine | None = None,
        provenance_tracker: ProvenanceTrackerEngine | None = None,
        explainability_provider: ExplainabilityProviderEngine | None = None,
        config: EvidenceConfig | None = None,
    ):
        self._verifier = verifier or EvidenceVerifierEngine()
        self._citation_generator = citation_generator or CitationGeneratorEngine()
        self._citation_formatter = citation_formatter or CitationFormatterEngine()
        self._coverage_analyzer = coverage_analyzer or CoverageAnalyzerEngine()
        self._source_ranker = source_ranker or SourceRankingEngine()
        self._conflict_detector = conflict_detector or ConflictDetectorEngine()
        self._confidence_calculator = confidence_calculator or ConfidenceCalculatorEngine()
        self._provenance_tracker = provenance_tracker or ProvenanceTrackerEngine()
        self._explainability_provider = explainability_provider or ExplainabilityProviderEngine()
        self._config = config or EvidenceConfig()

    async def run(
        self,
        spans: list[EvidenceSpan],
        citation_style: CitationStyle = CitationStyle.AMA,
        config_override: dict | None = None,
    ) -> PipelineResult:
        start = time.time()
        steps_completed: list[str] = []
        steps_skipped: list[str] = []
        errors: list[str] = []

        state = EvidenceState(
            spans=spans,
            config=config_override or {},
        )

        try:
            state.verification_results = await self._trace(
                ProvenanceAction.VERIFICATION,
                "EvidenceVerifierEngine",
                self._verifier.verify(spans, state),
                state,
            )
            steps_completed.append("verification")

            citation_task = self._trace(
                ProvenanceAction.CITATION,
                "CitationGeneratorEngine",
                self._citation_generator.generate(state.verification_results, state),
                state,
            )
            coverage_task = self._trace(
                ProvenanceAction.COVERAGE,
                "CoverageAnalyzerEngine",
                self._coverage_analyzer.analyze(state.verification_results, state),
                state,
            )
            conflict_task = self._trace(
                ProvenanceAction.CONFLICT,
                "ConflictDetectorEngine",
                self._conflict_detector.detect(state.verification_results, state),
                state,
            )

            citations, coverage, conflicts = await asyncio.gather(
                citation_task, coverage_task, conflict_task,
            )

            state.citations = citations
            state.coverage = coverage
            state.conflicts = conflicts
            steps_completed.extend(["citation", "coverage", "conflict_detection"])

            rank_task = self._trace(
                ProvenanceAction.RANKING,
                "SourceRankingEngine",
                self._source_ranker.rank(
                    [s for vr in state.verification_results for s in vr.supporting_sources + vr.contradicting_sources],
                    state,
                ),
                state,
            )
            state.ranked_sources = await rank_task
            steps_completed.append("ranking")

            state.citation_groups = await self._citation_generator.group_by_claim(state.citations)
            state.formatted_citation = await self._trace(
                ProvenanceAction.CITATION,
                "CitationFormatterEngine",
                self._citation_formatter.format(state.citations, citation_style),
                state,
            )

            state.confidence = await self._trace(
                ProvenanceAction.CONFIDENCE,
                "ConfidenceCalculatorEngine",
                self._confidence_calculator.calculate(
                    state.verification_results, state.coverage, state.conflicts, state.citations, state,
                ),
                state,
            )
            steps_completed.append("confidence")

            state.explanation = await self._trace(
                ProvenanceAction.EXPLANATION,
                "ExplainabilityProviderEngine",
                self._explainability_provider.explain(
                    state.verification_results, state.coverage, state.conflicts,
                    state.confidence, state.citations, state,
                ),
                state,
            )
            steps_completed.append("explanation")

        except Exception as e:
            errors.append(f"Pipeline error: {e}")
            raise EvidencePipelineError(f"Pipeline execution failed: {e}")

        total_time = round((time.time() - start) * 1000, 2)

        return PipelineResult(
            state=state,
            pipeline_name="evidence_pipeline",
            total_processing_time_ms=total_time,
            steps_completed=steps_completed,
            steps_skipped=steps_skipped,
            errors=errors,
            success=len(errors) == 0,
        )

    async def _trace(
        self,
        action: ProvenanceAction,
        engine_name: str,
        coro,
        state: EvidenceState,
    ):
        t0 = time.time()
        result = await coro
        elapsed = round((time.time() - t0) * 1000, 2)
        entry = ProvenanceEntry(
            action=action,
            engine_name=engine_name,
            processing_time_ms=elapsed,
            confidence=0.0,
        )
        state.provenance.append(entry)
        return result
