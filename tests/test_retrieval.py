"""Tests for retrieval fusion and metrics (pure functions, no models needed)."""

from core.agent.rag import reciprocal_rank_fusion, _tokenize
from core.eval.retrieval import (
    hit_at_k,
    recall_at_k,
    reciprocal_rank,
    ndcg_at_k,
)


class TestReciprocalRankFusion:
    def test_agreeing_rankings_reinforce(self):
        # Both retrievers rank 'a' first — it must win the fusion.
        fused = reciprocal_rank_fusion([["a", "b", "c"], ["a", "c", "b"]])
        assert fused[0][0] == "a"

    def test_item_in_both_beats_item_in_one(self):
        # 'b' appears in both lists; 'z' only in one — 'b' should rank higher.
        fused = dict(reciprocal_rank_fusion([["z", "b"], ["b", "y"]]))
        assert fused["b"] > fused["z"]
        assert fused["b"] > fused["y"]

    def test_k_smoothing_changes_scale_not_order(self):
        a = reciprocal_rank_fusion([["x", "y"]], k=10)
        b = reciprocal_rank_fusion([["x", "y"]], k=100)
        assert [i for i, _ in a] == [i for i, _ in b] == ["x", "y"]

    def test_empty(self):
        assert reciprocal_rank_fusion([]) == []


class TestTokenize:
    def test_lowercases_and_splits(self):
        assert _tokenize("Center Control!") == ["center", "control"]

    def test_keeps_alphanumeric(self):
        assert _tokenize("column 3 wins") == ["column", "3", "wins"]


class TestRetrievalMetrics:
    def test_hit_at_k(self):
        assert hit_at_k(["a", "b", "c"], {"c"}, 3) == 1.0
        assert hit_at_k(["a", "b", "c"], {"c"}, 2) == 0.0

    def test_recall_at_k(self):
        assert recall_at_k(["a", "b"], {"a", "b"}, 2) == 1.0
        assert recall_at_k(["a", "x"], {"a", "b"}, 2) == 0.5

    def test_reciprocal_rank(self):
        assert reciprocal_rank(["x", "a", "y"], {"a"}) == 0.5
        assert reciprocal_rank(["a"], {"a"}) == 1.0
        assert reciprocal_rank(["x", "y"], {"a"}) == 0.0

    def test_ndcg_rewards_higher_rank(self):
        high = ndcg_at_k(["a", "x", "y"], {"a"}, 3)
        low = ndcg_at_k(["x", "y", "a"], {"a"}, 3)
        assert high > low
        assert high == 1.0  # relevant item in first position is ideal
