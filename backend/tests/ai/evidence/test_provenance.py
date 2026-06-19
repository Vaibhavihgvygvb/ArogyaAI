from datetime import datetime

import pytest

from app.ai.evidence.engines.provenance import ProvenanceTrackerEngine
from app.ai.evidence.schemas import EvidenceState, ProvenanceAction, ProvenanceEntry


class TestProvenanceTrackerEngine:
    @pytest.mark.asyncio
    async def test_track_returns_list_with_entry(self):
        engine = ProvenanceTrackerEngine()
        entry = ProvenanceEntry(
            action=ProvenanceAction.VERIFICATION,
            engine_name="test_engine",
            processing_time_ms=10.5,
            confidence=0.85,
        )
        result = await engine.track(entry)
        assert len(result) == 1
        assert result[0].engine_name == "test_engine"

    @pytest.mark.asyncio
    async def test_track_returns_same_entry(self):
        engine = ProvenanceTrackerEngine()
        entry = ProvenanceEntry(
            action=ProvenanceAction.CITATION,
            engine_name="citation_engine",
            processing_time_ms=5.0,
            confidence=0.9,
        )
        result = await engine.track(entry)
        assert result[0].action == ProvenanceAction.CITATION
        assert result[0].engine_name == "citation_engine"

    @pytest.mark.asyncio
    async def test_track_appends_to_state_provenance(self):
        engine = ProvenanceTrackerEngine()
        state = EvidenceState()
        entry = ProvenanceEntry(
            action=ProvenanceAction.COVERAGE,
            engine_name="coverage_engine",
            processing_time_ms=3.0,
            confidence=0.7,
        )
        await engine.track(entry, state=state)
        assert len(state.provenance) == 1
        assert state.provenance[0].engine_name == "coverage_engine"

    @pytest.mark.asyncio
    async def test_track_appends_multiple_entries_to_state(self):
        engine = ProvenanceTrackerEngine()
        state = EvidenceState()
        entries = [
            ProvenanceEntry(
                action=ProvenanceAction.VERIFICATION,
                engine_name="verifier",
                processing_time_ms=5.0,
                confidence=0.8,
            ),
            ProvenanceEntry(
                action=ProvenanceAction.CONFLICT,
                engine_name="conflict_detector",
                processing_time_ms=3.0,
                confidence=0.9,
            ),
        ]
        for e in entries:
            await engine.track(e, state=state)
        assert len(state.provenance) == 2

    @pytest.mark.asyncio
    async def test_track_returns_entry_even_without_state(self):
        engine = ProvenanceTrackerEngine()
        entry = ProvenanceEntry(
            action=ProvenanceAction.CONFIDENCE,
            engine_name="confidence_calc",
            processing_time_ms=2.0,
            confidence=0.95,
        )
        result = await engine.track(entry)
        assert len(result) == 1
        assert result[0].engine_name == "confidence_calc"

    @pytest.mark.asyncio
    async def test_get_graph_with_empty_entries_returns_default_dict(self):
        engine = ProvenanceTrackerEngine()
        result = await engine.get_graph([])
        assert result == {"entries": [], "total_time_ms": 0.0, "engine_count": 0}

    @pytest.mark.asyncio
    async def test_get_graph_calculates_total_time_ms(self):
        engine = ProvenanceTrackerEngine()
        entries = [
            ProvenanceEntry(
                action=ProvenanceAction.VERIFICATION,
                engine_name="verifier",
                processing_time_ms=10.0,
                confidence=0.8,
            ),
            ProvenanceEntry(
                action=ProvenanceAction.CITATION,
                engine_name="citer",
                processing_time_ms=20.0,
                confidence=0.9,
            ),
        ]
        result = await engine.get_graph(entries)
        assert result["total_time_ms"] == 30.0

    @pytest.mark.asyncio
    async def test_get_graph_total_time_is_rounded(self):
        engine = ProvenanceTrackerEngine()
        entries = [
            ProvenanceEntry(
                action=ProvenanceAction.VERIFICATION,
                engine_name="verifier",
                processing_time_ms=10.123,
                confidence=0.8,
            ),
        ]
        result = await engine.get_graph(entries)
        assert result["total_time_ms"] == 10.12

    @pytest.mark.asyncio
    async def test_get_graph_counts_engines(self):
        engine = ProvenanceTrackerEngine()
        entries = [
            ProvenanceEntry(
                action=ProvenanceAction.VERIFICATION,
                engine_name="verifier",
                processing_time_ms=5.0,
                confidence=0.8,
            ),
            ProvenanceEntry(
                action=ProvenanceAction.CITATION,
                engine_name="citer",
                processing_time_ms=5.0,
                confidence=0.8,
            ),
            ProvenanceEntry(
                action=ProvenanceAction.COVERAGE,
                engine_name="coverage",
                processing_time_ms=5.0,
                confidence=0.8,
            ),
        ]
        result = await engine.get_graph(entries)
        assert result["engine_count"] == 3

    @pytest.mark.asyncio
    async def test_get_graph_returns_structured_dict(self):
        engine = ProvenanceTrackerEngine()
        ts = datetime(2025, 1, 1, 12, 0, 0)
        entries = [
            ProvenanceEntry(
                action=ProvenanceAction.VERIFICATION,
                timestamp=ts,
                engine_name="verifier",
                input_summary="input data",
                output_summary="verified",
                processing_time_ms=5.0,
                confidence=0.85,
            ),
        ]
        result = await engine.get_graph(entries)
        assert len(result["entries"]) == 1
        entry = result["entries"][0]
        assert entry["action"] == "verification"
        assert entry["engine"] == "verifier"
        assert entry["time_ms"] == 5.0
        assert entry["confidence"] == 0.85
        assert entry["timestamp"] == "2025-01-01T12:00:00"

    @pytest.mark.asyncio
    async def test_get_graph_entry_without_timestamp(self):
        engine = ProvenanceTrackerEngine()
        entries = [
            ProvenanceEntry(
                action=ProvenanceAction.RANKING,
                engine_name="ranker",
                processing_time_ms=1.0,
                confidence=0.5,
            ),
        ]
        entries[0].timestamp = None
        result = await engine.get_graph(entries)
        assert result["entries"][0]["timestamp"] is None

    @pytest.mark.asyncio
    async def test_track_keeps_entry_data_intact(self):
        engine = ProvenanceTrackerEngine()
        entry = ProvenanceEntry(
            action=ProvenanceAction.EXPLANATION,
            engine_name="explainer",
            input_summary="input",
            output_summary="output",
            processing_time_ms=7.5,
            confidence=0.92,
            metadata={"key": "value"},
        )
        result = await engine.track(entry)
        assert result[0].input_summary == "input"
        assert result[0].output_summary == "output"
        assert result[0].processing_time_ms == 7.5
        assert result[0].confidence == 0.92
        assert result[0].metadata == {"key": "value"}

    @pytest.mark.asyncio
    async def test_get_graph_structure_keys(self):
        engine = ProvenanceTrackerEngine()
        entries = [
            ProvenanceEntry(
                action=ProvenanceAction.PIPELINE,
                engine_name="pipeline",
                processing_time_ms=1.0,
                confidence=0.5,
            ),
        ]
        result = await engine.get_graph(entries)
        assert "entries" in result
        assert "total_time_ms" in result
        assert "engine_count" in result
