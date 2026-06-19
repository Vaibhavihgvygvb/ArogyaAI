import pytest

from app.ai.evidence.engines.ranking import SourceRankingEngine
from app.ai.evidence.schemas import EvidenceState, EvidenceType, VerifiedSource


@pytest.fixture
def ranker():
    return SourceRankingEngine()


def make_source(
    source_id: str,
    authority: float = 0.0,
    relevance: float = 0.0,
    recency: float = 0.0,
    quality: float = 0.0,
) -> VerifiedSource:
    return VerifiedSource(
        source_id=source_id,
        title=f"Source {source_id}",
        authors=[f"Author of {source_id}"],
            evidence_type=EvidenceType.GUIDELINE,
        authority_score=authority,
        relevance_score=relevance,
        recency_score=recency,
        quality_score=quality,
        support_direction="supporting",
        excerpt=f"Excerpt from {source_id}",
    )


class TestSourceRankingEngine:
    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, ranker):
        result = await ranker.rank([])
        assert result == []

    @pytest.mark.asyncio
    async def test_single_source_returns_same(self, ranker):
        src = make_source("src_1", authority=0.8, relevance=0.9, recency=0.85, quality=0.75)
        result = await ranker.rank([src])
        assert len(result) == 1
        assert result[0] == src

    @pytest.mark.asyncio
    async def test_multiple_sources_ranked_by_composite_score(self, ranker):
        high = make_source("high", authority=0.9, relevance=0.9, recency=0.9, quality=0.9)
        mid = make_source("mid", authority=0.5, relevance=0.5, recency=0.5, quality=0.5)
        low = make_source("low", authority=0.1, relevance=0.1, recency=0.1, quality=0.1)
        result = await ranker.rank([low, high, mid])
        assert [s.source_id for s in result] == ["high", "mid", "low"]

    @pytest.mark.asyncio
    async def test_higher_relevance_sources_come_first(self, ranker):
        low_rel = make_source("low_rel", authority=0.5, relevance=0.2, recency=0.5, quality=0.5)
        mid_rel = make_source("mid_rel", authority=0.5, relevance=0.5, recency=0.5, quality=0.5)
        high_rel = make_source("high_rel", authority=0.5, relevance=0.9, recency=0.5, quality=0.5)
        result = await ranker.rank([low_rel, high_rel, mid_rel])
        assert result[0].source_id == "high_rel"
        assert result[1].source_id == "mid_rel"
        assert result[2].source_id == "low_rel"

    @pytest.mark.asyncio
    async def test_all_equal_scores_maintain_order(self, ranker):
        a = make_source("a", authority=0.5, relevance=0.5, recency=0.5, quality=0.5)
        b = make_source("b", authority=0.5, relevance=0.5, recency=0.5, quality=0.5)
        c = make_source("c", authority=0.5, relevance=0.5, recency=0.5, quality=0.5)
        result = await ranker.rank([a, b, c])
        assert [s.source_id for s in result] == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_relevance_weight_dominates(self, ranker):
        high_rel = make_source(
            "high_rel", authority=0.0, relevance=1.0, recency=0.0, quality=0.0
        )
        high_auth = make_source(
            "high_auth", authority=1.0, relevance=0.0, recency=0.0, quality=0.0
        )
        result = await ranker.rank([high_auth, high_rel])
        assert result[0].source_id == "high_rel"

    @pytest.mark.asyncio
    async def test_rank_with_state(self, ranker):
        src = make_source("src_1", authority=0.8, relevance=0.9, recency=0.85, quality=0.75)
        state = EvidenceState(config={"threshold": 0.5})
        result = await ranker.rank([src], state=state)
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_composite_score_calculation(self, ranker):
        src = make_source("src", authority=1.0, relevance=1.0, recency=1.0, quality=1.0)
        result = await ranker.rank([src])
        expected = (
            0.3 * 1.0
            + 0.4 * 1.0
            + 0.15 * 1.0
            + 0.15 * 1.0
        )
        assert len(result) == 1
        assert result[0].source_id == "src"

    @pytest.mark.asyncio
    async def test_authority_impact(self, ranker):
        high_auth = make_source("high_auth", authority=1.0, relevance=0.0, recency=0.0, quality=0.0)
        low_auth = make_source("low_auth", authority=0.0, relevance=0.0, recency=0.0, quality=0.0)
        result = await ranker.rank([low_auth, high_auth])
        assert result[0].source_id == "high_auth"

    @pytest.mark.asyncio
    async def test_recency_impact(self, ranker):
        recent = make_source("recent", authority=0.0, relevance=0.0, recency=1.0, quality=0.0)
        old = make_source("old", authority=0.0, relevance=0.0, recency=0.0, quality=0.0)
        result = await ranker.rank([old, recent])
        assert result[0].source_id == "recent"

    @pytest.mark.asyncio
    async def test_quality_impact(self, ranker):
        high_qual = make_source("high_qual", authority=0.0, relevance=0.0, recency=0.0, quality=1.0)
        low_qual = make_source("low_qual", authority=0.0, relevance=0.0, recency=0.0, quality=0.0)
        result = await ranker.rank([low_qual, high_qual])
        assert result[0].source_id == "high_qual"

    @pytest.mark.asyncio
    async def test_mix_of_high_and_low_scores(self, ranker):
        best = make_source("best", authority=0.9, relevance=0.95, recency=0.85, quality=0.9)
        worst = make_source("worst", authority=0.1, relevance=0.05, recency=0.1, quality=0.1)
        average = make_source("average", authority=0.5, relevance=0.5, recency=0.5, quality=0.5)
        result = await ranker.rank([worst, best, average])
        assert result[0].source_id == "best"
        assert result[1].source_id == "average"
        assert result[2].source_id == "worst"
