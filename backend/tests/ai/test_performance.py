import asyncio
import time
from datetime import datetime
from uuid import uuid4

import pytest

from app.ai.clinical_safety.pipelines.pipeline import ClinicalSafetyPipeline
from app.ai.clinical_safety.schemas import (
    ClinicalRiskReport,
    ClinicalRiskResult,
    ComplianceCheck,
    ComplianceReport,
    DisclaimerConfig,
    DisclaimerResult,
    DisclaimerType,
    EmergencyReport,
    EmergencyResult,
    HallucinationReport,
    HallucinationResult,
    HallucinationType,
    PHIValidationReport,
    PHIFinding,
    PHIType,
    RiskLevel,
    SafetyServiceResult,
    SupportLevel,
    UnsupportedClaim,
    UnsupportedClaimReport,
)
from app.ai.clinical_safety.services._service import ClinicalSafetyService
from app.ai.clinical_safety.services.compliance import DefaultComplianceValidator
from app.ai.clinical_safety.services.hallucination import DefaultHallucinationDetector
from app.ai.clinical_safety.services.phi import DefaultPHIValidator
from app.ai.evidence.config import EvidenceConfig
from app.ai.evidence.pipeline import EvidencePipeline
from app.ai.evidence.schemas import (
    Citation,
    CitationStyle,
    ConfidenceResult,
    ConflictResult,
    CoverageResult,
    EvidenceSpan,
    EvidenceState,
    ExplanationResult,
    FormattedCitation,
    PipelineResult,
    VerificationResult,
    VerificationStatus,
    VerifiedSource,
)
from app.ai.evidence.service import EvidenceService
from app.ai.evaluation.schemas import EvaluationMetric, EvaluationRun, MetricCategory


class _MockVerifier:
    async def verify(self, spans, state=None):
        return [
            VerificationResult(
                span=s,
                verified=True,
                status=VerificationStatus.VERIFIED,
                supporting_sources=[
                    VerifiedSource(
                        source_id="s1",
                        support_direction="supporting",
                        authority_score=0.8,
                        relevance_score=0.9,
                        recency_score=0.7,
                        quality_score=0.85,
                    )
                ],
                contradicting_sources=[],
                confidence=0.9,
                evidence_summary=f"Verified: {s.claim}",
                verification_details="Mock verification",
            )
            for s in spans
        ]


class _MockCitationGenerator:
    async def generate(self, verification_results, state=None):
        citations = []
        for i, vr in enumerate(verification_results):
            for j, src in enumerate(vr.supporting_sources):
                citations.append(
                    Citation(
                        citation_id=f"cit_{i}_{j}",
                        span_index=i,
                        evidence_text=vr.span.claim,
                        source=src,
                        inline_ref="(90% confidence)",
                        confidence=vr.confidence,
                    )
                )
        return citations

    async def group_by_claim(self, citations):
        return []


class _MockCitationFormatter:
    async def format(self, citations, style=CitationStyle.AMA):
        return FormattedCitation(style=style, text="Formatted text", markdown="**Formatted**")


class _MockCoverageAnalyzer:
    async def analyze(self, verification_results, state=None):
        return CoverageResult(
            total_spans=len(verification_results),
            verified_spans=len(verification_results),
            unverified_spans=0,
            partially_verified_spans=0,
            coverage_score=1.0,
            evidence_density=1.0,
            gaps=[],
            recommendations=["Good coverage."],
        )


class _MockSourceRanker:
    async def rank(self, sources, state=None):
        return sorted(sources, key=lambda s: s.relevance_score, reverse=True)


class _MockConflictDetector:
    async def detect(self, verification_results, state=None):
        return []


class _MockConfidenceCalculator:
    async def calculate(self, verification_results, coverage, conflicts, citations, state=None):
        return ConfidenceResult(
            overall=0.85,
            verification_confidence=0.9,
            citation_confidence=0.85,
            coverage_confidence=1.0,
            source_quality_confidence=0.75,
            suitable_for_ai=True,
            breakdown=[],
            warnings=[],
        )


class _MockProvenanceTracker:
    pass


class _MockExplainabilityProvider:
    async def explain(self, verification_results, coverage, conflicts, confidence, citations, state=None):
        return ExplanationResult(
            summary="All evidence verified successfully.",
            recommendations=["Review any conflicts."],
        )


def _make_pipeline() -> EvidencePipeline:
    return EvidencePipeline(
        verifier=_MockVerifier(),
        citation_generator=_MockCitationGenerator(),
        citation_formatter=_MockCitationFormatter(),
        coverage_analyzer=_MockCoverageAnalyzer(),
        source_ranker=_MockSourceRanker(),
        conflict_detector=_MockConflictDetector(),
        confidence_calculator=_MockConfidenceCalculator(),
        provenance_tracker=_MockProvenanceTracker(),
        explainability_provider=_MockExplainabilityProvider(),
        config=EvidenceConfig(EVIDENCE_MAX_SPANS=200),
    )


class EvaluationRunner:
    def __init__(self):
        self.runs: list[EvaluationRun] = []

    async def create_run(
        self,
        pipeline_name: str,
        metrics: list[EvaluationMetric],
    ) -> EvaluationRun:
        run = EvaluationRun(
            id=str(uuid4()),
            timestamp=datetime.utcnow(),
            pipeline_name=pipeline_name,
            metrics=metrics,
            summary_score=sum(m.value * m.weight for m in metrics) / sum(m.weight for m in metrics) if metrics else 0.0,
            passed=all(m.passed is not False for m in metrics),
        )
        self.runs.append(run)
        return run

    async def generate_report(self, run: EvaluationRun) -> dict:
        total = len(run.metrics)
        passed = sum(1 for m in run.metrics if m.passed is not False)
        failed = total - passed
        return {
            "run_id": run.id,
            "pipeline": run.pipeline_name,
            "total_metrics": total,
            "passed": passed,
            "failed": failed,
            "summary_score": round(run.summary_score, 4),
            "overall_passed": run.passed,
        }


def _measure(iterations: int, fn, *args, **kwargs) -> dict:
    times: list[float] = []
    for _ in range(iterations):
        t0 = time.time()
        fn(*args, **kwargs)
        times.append((time.time() - t0) * 1000)
    return {
        "min": round(min(times), 2),
        "max": round(max(times), 2),
        "avg": round(sum(times) / len(times), 2),
        "times": times,
    }


def _measure_async(iterations: int, coro_fn, *args, **kwargs) -> dict:
    times: list[float] = []
    for _ in range(iterations):
        t0 = time.time()
        asyncio.run(coro_fn(*args, **kwargs))
        times.append((time.time() - t0) * 1000)
    return {
        "min": round(min(times), 2),
        "max": round(max(times), 2),
        "avg": round(sum(times) / len(times), 2),
        "times": times,
    }


def _make_medical_claim(text: str) -> EvidenceSpan:
    return EvidenceSpan(text=text, claim=text, span_start=0, span_end=len(text))


def _print_results(label: str, stats: dict, threshold: float) -> None:
    print(f"  [{label}] min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <{threshold}ms)")
    assert stats["avg"] < threshold, f"{label}: avg {stats['avg']}ms exceeds threshold {threshold}ms"


@pytest.mark.asyncio
class TestPipelineLatency:

    async def test_evidence_pipeline_latency(self):
        pipeline = _make_pipeline()
        iterations = 3

        for n_spans, threshold, label in [
            (1, 50, "1 span"),
            (5, 200, "5 spans"),
            (10, 500, "10 spans"),
        ]:
            spans = [_make_medical_claim(f"Test claim number {i} about medical treatment.") for i in range(n_spans)]
            times: list[float] = []
            for _ in range(iterations):
                t0 = time.time()
                await pipeline.run(spans)
                times.append((time.time() - t0) * 1000)
            stats = {"min": round(min(times), 2), "max": round(max(times), 2), "avg": round(sum(times) / len(times), 2)}
            print(f"  EvidencePipeline [{label}]: min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <{threshold}ms)")
            assert stats["avg"] < threshold, f"EvidencePipeline {label}: avg {stats['avg']}ms exceeds {threshold}ms"

    async def test_safety_pipeline_latency(self):
        pipeline = ClinicalSafetyPipeline()
        iterations = 3

        cases = [
            ("short", "The patient has a mild fever and cough. Rest and hydration are recommended.", 50),
            ("medium", "The patient presents with diabetes and hypertension. " * 10, 200),
            ("long", "Clinical assessment indicates " + ("chronic condition management " * 100), 500),
        ]

        for label, text, threshold in cases:
            claims = ["diabetes requires monitoring", "hypertension treatment"]
            times: list[float] = []
            for _ in range(iterations):
                t0 = time.time()
                await pipeline.run(text=text, claims=claims)
                times.append((time.time() - t0) * 1000)
            stats = {"min": round(min(times), 2), "max": round(max(times), 2), "avg": round(sum(times) / len(times), 2)}
            print(f"  SafetyPipeline [{label}]: min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <{threshold}ms)")
            assert stats["avg"] < threshold, f"SafetyPipeline {label}: avg {stats['avg']}ms exceeds {threshold}ms"

    async def test_hallucination_detection_latency(self):
        detector = DefaultHallucinationDetector()
        iterations = 3

        for n_claims, threshold, label in [
            (1, 50, "1 claim"),
            (10, 200, "10 claims"),
            (50, 500, "50 claims"),
        ]:
            claims = [f"The medication xylomycin-{i} is effective for treating condition-{i}." for i in range(n_claims)]
            times: list[float] = []
            for _ in range(iterations):
                t0 = time.time()
                await detector.detect("", claims, None)
                times.append((time.time() - t0) * 1000)
            stats = {"min": round(min(times), 2), "max": round(max(times), 2), "avg": round(sum(times) / len(times), 2)}
            print(f"  HallucinationDetection [{label}]: min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <{threshold}ms)")
            assert stats["avg"] < threshold, f"HallucinationDetection {label}: avg {stats['avg']}ms exceeds {threshold}ms"

    async def test_phi_validation_latency(self):
        validator = DefaultPHIValidator()
        iterations = 3

        clean_cases = [
            ("clean short", "The patient has a mild fever and cough.", 50),
            ("clean long", " ".join(["The patient reports no significant symptoms." for _ in range(50)]), 200),
        ]

        phi_laden_cases = [
            ("phi short", "SSN: 123-45-6789, Email: test@example.com, Phone: 9876543210, Passport: AB123456", 50),
            ("phi long", " ".join([
                "SSN: 123-45-6789, Email: user@domain.com, Aadhaar: 1234 5678 9012, "
                "Phone: 9876543210, Passport: AB123456, Card: 4111111111111111"
                for _ in range(20)
            ]), 500),
        ]

        for label, text, threshold in clean_cases:
            times: list[float] = []
            for _ in range(iterations):
                t0 = time.time()
                await validator.validate(text)
                times.append((time.time() - t0) * 1000)
            stats = {"min": round(min(times), 2), "max": round(max(times), 2), "avg": round(sum(times) / len(times), 2)}
            print(f"  PHIValidation [{label}]: min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <{threshold}ms)")
            assert stats["avg"] < threshold, f"PHIValidation {label}: avg {stats['avg']}ms exceeds {threshold}ms"

        for label, text, threshold in phi_laden_cases:
            times: list[float] = []
            for _ in range(iterations):
                t0 = time.time()
                await validator.validate(text)
                times.append((time.time() - t0) * 1000)
            stats = {"min": round(min(times), 2), "max": round(max(times), 2), "avg": round(sum(times) / len(times), 2)}
            print(f"  PHIValidation [{label}]: min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <{threshold}ms)")
            assert stats["avg"] < threshold, f"PHIValidation {label}: avg {stats['avg']}ms exceeds {threshold}ms"

    async def test_compliance_latency(self):
        validator = DefaultComplianceValidator()
        iterations = 3

        hallucination_report = HallucinationReport(
            results=[
                HallucinationResult(
                    claim="Test medication claim",
                    hallucination_type=HallucinationType.UNKNOWN,
                    confidence=0.1,
                    details="No issue",
                )
            ],
            total_claims=1,
            hallucinated_count=0,
            hallucination_rate=0.0,
            passed=True,
        )
        unsupported_report = UnsupportedClaimReport(
            claims=[
                UnsupportedClaim(
                    claim="Test claim",
                    support_level=SupportLevel.FULLY_SUPPORTED,
                    confidence=0.9,
                    matched_evidence=["evidence"],
                    missing_evidence=[],
                )
            ],
            total_claims=1,
            supported_count=1,
            unsupported_count=0,
            contradictory_count=0,
            coverage_score=1.0,
            passed=True,
        )
        disclaimer_result = DisclaimerResult(
            selected_disclaimers=[
                DisclaimerConfig(
                    disclaimer_type=DisclaimerType.GENERAL_MEDICAL,
                    text="General medical disclaimer",
                    severity="informational",
                    required=True,
                )
            ],
            has_emergency_disclaimer=False,
            has_medication_disclaimer=False,
            has_mental_health_disclaimer=False,
        )
        risk_report = ClinicalRiskReport(
            results=[
                ClinicalRiskResult(
                    risk_level=RiskLevel.LOW,
                    score=0.1,
                    factors=["No concerns"],
                    confidence_impact=0.0,
                    unsupported_impact=0.0,
                    topic_sensitivity=0.0,
                    emergency_indicators=[],
                )
            ],
            overall_risk=RiskLevel.LOW,
            max_risk_score=0.1,
            passed=True,
        )

        times: list[float] = []
        for _ in range(iterations):
            t0 = time.time()
            await validator.validate(hallucination_report, unsupported_report, disclaimer_result, risk_report)
            times.append((time.time() - t0) * 1000)
        stats = {"min": round(min(times), 2), "max": round(max(times), 2), "avg": round(sum(times) / len(times), 2)}
        print(f"  ComplianceValidation: min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <200ms)")
        assert stats["avg"] < 200, f"ComplianceValidation: avg {stats['avg']}ms exceeds 200ms"


@pytest.mark.asyncio
class TestServiceLatency:

    async def test_evidence_service_latency(self):
        pipeline = _make_pipeline()
        service = EvidenceService(pipeline=pipeline, config=EvidenceConfig(EVIDENCE_MAX_SPANS=200))
        iterations = 3

        cases = [
            (1, 50, "1 span"),
            (5, 200, "5 spans"),
            (10, 500, "10 spans"),
        ]

        for n_spans, threshold, label in cases:
            spans = [_make_medical_claim(f"Clinical evidence claim number {i} about patient treatment outcomes.") for i in range(n_spans)]
            times: list[float] = []
            for _ in range(iterations):
                t0 = time.time()
                await service.validate_evidence(spans)
                times.append((time.time() - t0) * 1000)
            stats = {"min": round(min(times), 2), "max": round(max(times), 2), "avg": round(sum(times) / len(times), 2)}
            print(f"  EvidenceService [{label}]: min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <{threshold}ms)")
            assert stats["avg"] < threshold, f"EvidenceService {label}: avg {stats['avg']}ms exceeds {threshold}ms"

    async def test_safety_service_latency(self):
        service = ClinicalSafetyService()
        iterations = 3

        cases = [
            ("short clean", "The patient has a mild fever and cough. Rest and hydration are recommended.", [], 50),
            ("medium with claims", "The patient presents with diabetes and hypertension. " * 10, ["diabetes requires monitoring", "hypertension treatment"], 200),
            ("long complex", "Clinical assessment: " + ("patient reports chronic headache and dizziness " * 50), ["chronic headache needs evaluation", "dizziness may indicate underlying condition"], 500),
        ]

        for label, text, claims, threshold in cases:
            times: list[float] = []
            for _ in range(iterations):
                t0 = time.time()
                await service.validate(response_text=text, claims=claims)
                times.append((time.time() - t0) * 1000)
            stats = {"min": round(min(times), 2), "max": round(max(times), 2), "avg": round(sum(times) / len(times), 2)}
            print(f"  SafetyService [{label}]: min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <{threshold}ms)")
            assert stats["avg"] < threshold, f"SafetyService {label}: avg {stats['avg']}ms exceeds {threshold}ms"

    async def test_evaluation_runner_latency(self):
        runner = EvaluationRunner()
        iterations = 3

        run_times: list[float] = []
        for _ in range(iterations):
            t0 = time.time()
            run = await runner.create_run(
                pipeline_name="evidence_pipeline",
                metrics=[
                    EvaluationMetric(name="precision", category=MetricCategory.EVIDENCE, value=0.95, weight=1.0, passed=True),
                    EvaluationMetric(name="recall", category=MetricCategory.EVIDENCE, value=0.87, weight=1.0, passed=True),
                    EvaluationMetric(name="latency", category=MetricCategory.LATENCY, value=150.0, weight=0.5, passed=True),
                ],
            )
            _ = run
            run_times.append((time.time() - t0) * 1000)

        stats = {"min": round(min(run_times), 2), "max": round(max(run_times), 2), "avg": round(sum(run_times) / len(run_times), 2)}
        print(f"  EvaluationRunner.create_run: min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <50ms)")
        assert stats["avg"] < 50, f"EvaluationRunner.create_run: avg {stats['avg']}ms exceeds 50ms"

        report_times: list[float] = []
        run = await runner.create_run(
            pipeline_name="safety_pipeline",
            metrics=[EvaluationMetric(name="safety_score", category=MetricCategory.SAFETY, value=1.0, weight=1.0, passed=True)],
        )
        for _ in range(iterations):
            t0 = time.time()
            await runner.generate_report(run)
            report_times.append((time.time() - t0) * 1000)

        stats = {"min": round(min(report_times), 2), "max": round(max(report_times), 2), "avg": round(sum(report_times) / len(report_times), 2)}
        print(f"  EvaluationRunner.generate_report: min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <50ms)")
        assert stats["avg"] < 50, f"EvaluationRunner.generate_report: avg {stats['avg']}ms exceeds 50ms"


@pytest.mark.asyncio
class TestThroughput:

    async def test_concurrent_safety_validations(self):
        service = ClinicalSafetyService()
        texts = [
            ("The patient has a mild fever and cough.", ["fever", "cough"]),
            ("Patient reports chest pain and shortness of breath.", ["chest pain", "shortness of breath"]),
            ("Diabetes and hypertension require ongoing management.", ["diabetes", "hypertension"]),
            ("The medication should be taken twice daily with food.", ["medication dosage"]),
            ("Patient has a history of asthma and allergies.", ["asthma", "allergies"]),
            ("Annual physical examination is recommended.", ["physical examination"]),
            ("The lab results indicate normal kidney function.", ["lab results", "kidney function"]),
            ("Vaccination schedule should be followed as per guidelines.", ["vaccination"]),
            ("Mental health assessment is part of the comprehensive evaluation.", ["mental health"]),
            ("Follow-up appointment is scheduled in two weeks.", ["follow-up"]),
        ]
        iterations = 3

        times: list[float] = []
        for _ in range(iterations):
            t0 = time.time()
            results = await asyncio.gather(*[
                service.validate(response_text=text, claims=claims)
                for text, claims in texts
            ])
            assert len(results) == 10
            times.append((time.time() - t0) * 1000)

        stats = {"min": round(min(times), 2), "max": round(max(times), 2), "avg": round(sum(times) / len(times), 2)}
        print(f"  ConcurrentSafety (10 parallel): min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <2000ms)")
        assert stats["avg"] < 2000, f"ConcurrentSafety: avg {stats['avg']}ms exceeds 2000ms"

    async def test_bulk_evidence_validation(self):
        pipeline = _make_pipeline()
        iterations = 3

        spans = [_make_medical_claim(f"Bulk evidence claim number {i} for performance measurement of the evidence pipeline.") for i in range(100)]
        times: list[float] = []
        for _ in range(iterations):
            t0 = time.time()
            result = await pipeline.run(spans)
            assert result.success
            times.append((time.time() - t0) * 1000)

        stats = {"min": round(min(times), 2), "max": round(max(times), 2), "avg": round(sum(times) / len(times), 2)}
        print(f"  BulkEvidence (100 spans): min={stats['min']}ms  max={stats['max']}ms  avg={stats['avg']}ms  (threshold: <2000ms)")
        assert stats["avg"] < 2000, f"BulkEvidence: avg {stats['avg']}ms exceeds 2000ms"
