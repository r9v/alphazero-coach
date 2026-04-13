"""Tests for game API routes with mocked Engine."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from core.api.routes import router, set_engine, _usage
from core.engine import MoveStats, EvalResult
from tests.conftest import make_session, make_eval_result


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    session = make_session(move_history=[])
    engine.new_game.return_value = session
    engine.get_session.return_value = session
    engine.player_move.return_value = session
    engine.ai_move.return_value = session
    engine.evaluate_position.return_value = make_eval_result()
    return engine


@pytest.fixture
def client(mock_engine):
    app = FastAPI()
    app.include_router(router)
    set_engine(mock_engine)
    _usage.clear()
    return TestClient(app)


class TestNewGame:
    def test_success(self, client):
        resp = client.post("/game/new")
        assert resp.status_code == 200
        data = resp.json()
        assert "game_id" in data
        assert "board" in data
        assert data["move_number"] == 0

    @patch("core.api.routes.MAX_GAMES_PER_DAY", 1)
    def test_rate_limit(self, client):
        # First game should succeed
        resp1 = client.post("/game/new")
        assert resp1.status_code == 200

        # Second should be rate-limited
        resp2 = client.post("/game/new")
        assert resp2.status_code == 429
        assert "Demo limit" in resp2.json()["detail"]


class TestPlayerMove:
    def test_success(self, client, mock_engine):
        resp = client.post("/game/test123/move", json={"column": 3})
        assert resp.status_code == 200
        mock_engine.player_move.assert_called_once_with("test123", 3)

    def test_invalid_column(self, client):
        resp = client.post("/game/test123/move", json={"column": 9})
        assert resp.status_code == 422  # Pydantic validation

    def test_game_not_found(self, client, mock_engine):
        mock_engine.get_session.return_value = None
        resp = client.post("/game/unknown/move", json={"column": 3})
        assert resp.status_code == 404

    def test_illegal_move(self, client, mock_engine):
        mock_engine.player_move.side_effect = ValueError("Column 3 is not a legal move")
        resp = client.post("/game/test123/move", json={"column": 3})
        assert resp.status_code == 400


class TestAiMove:
    def test_success(self, client, mock_engine):
        resp = client.post("/game/test123/ai-move")
        assert resp.status_code == 200
        mock_engine.ai_move.assert_called_once_with("test123")

    def test_game_not_found(self, client, mock_engine):
        mock_engine.get_session.return_value = None
        resp = client.post("/game/unknown/ai-move")
        assert resp.status_code == 404


class TestEvaluate:
    def test_success(self, client):
        resp = client.post("/game/test123/evaluate")
        assert resp.status_code == 200
        data = resp.json()
        assert "best_action" in data
        assert "move_stats" in data
        assert len(data["move_stats"]) == 3

    def test_game_not_found(self, client, mock_engine):
        mock_engine.get_session.return_value = None
        resp = client.post("/game/unknown/evaluate")
        assert resp.status_code == 404
