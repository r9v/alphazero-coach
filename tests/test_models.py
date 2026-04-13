"""Tests for Pydantic request/response models."""

import pytest
from pydantic import ValidationError

from core.api.models import MoveRequest, GameStateResponse, EvalResponse, MoveStatsResponse


class TestMoveRequest:
    def test_valid_columns(self):
        for col in range(7):
            req = MoveRequest(column=col)
            assert req.column == col

    def test_column_too_low(self):
        with pytest.raises(ValidationError):
            MoveRequest(column=-1)

    def test_column_too_high(self):
        with pytest.raises(ValidationError):
            MoveRequest(column=7)

    def test_non_integer(self):
        with pytest.raises(ValidationError):
            MoveRequest(column="abc")


class TestGameStateResponse:
    def test_round_trip(self):
        data = {
            "game_id": "abc123",
            "board": [[0] * 7 for _ in range(6)],
            "player": -1,
            "is_terminal": False,
            "winner": None,
            "legal_actions": [0, 1, 2, 3, 4, 5, 6],
            "move_history": [],
            "move_number": 0,
        }
        resp = GameStateResponse(**data)
        dumped = resp.model_dump()
        assert dumped["game_id"] == "abc123"
        assert dumped["player"] == -1
        assert len(dumped["board"]) == 6
        assert len(dumped["legal_actions"]) == 7

    def test_terminal_with_winner(self):
        data = {
            "game_id": "xyz",
            "board": [[0] * 7 for _ in range(6)],
            "player": 1,
            "is_terminal": True,
            "winner": -1,
            "legal_actions": [],
            "move_history": [3, 3, 4, 4, 5, 5, 6],
            "move_number": 7,
        }
        resp = GameStateResponse(**data)
        assert resp.is_terminal is True
        assert resp.winner == -1


class TestEvalResponse:
    def test_with_move_stats(self):
        resp = EvalResponse(
            best_action=3,
            root_value=0.5,
            total_simulations=400,
            move_stats=[
                MoveStatsResponse(column=3, visits=300, q_value=0.5, prior=0.6, visit_share=0.75),
                MoveStatsResponse(column=4, visits=100, q_value=0.1, prior=0.3, visit_share=0.25),
            ],
        )
        assert resp.best_action == 3
        assert len(resp.move_stats) == 2
        assert resp.move_stats[0].visit_share == 0.75
