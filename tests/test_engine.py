"""Tests for GameSession properties and Engine caching."""

import numpy as np

from core.engine import GameSession, EvalResult, MoveStats
from tests.conftest import make_game_state, make_session, make_eval_result


class TestGameSession:
    def test_move_number(self):
        session = make_session(move_history=[3, 4, 2])
        assert session.move_number == 3

    def test_move_number_empty(self):
        session = make_session(move_history=[])
        assert session.move_number == 0

    def test_player(self):
        session = make_session(player=-1)
        assert session.player == -1

    def test_board_is_list(self):
        board = np.zeros((6, 7), dtype=int)
        session = make_session(board=board)
        result = session.board
        assert isinstance(result, list)
        assert isinstance(result[0], list)

    def test_is_terminal_false(self):
        session = make_session(terminal=False)
        assert session.is_terminal is False

    def test_is_terminal_true(self):
        session = make_session(terminal=True)
        assert session.is_terminal is True

    def test_winner_not_terminal(self):
        session = make_session(terminal=False)
        assert session.winner is None

    def test_winner_red(self):
        session = make_session(terminal=True, terminal_value=-1)
        assert session.winner == -1

    def test_winner_yellow(self):
        session = make_session(terminal=True, terminal_value=1)
        assert session.winner == 1

    def test_winner_draw(self):
        session = make_session(terminal=True, terminal_value=0)
        assert session.winner is None  # draw returns None

    def test_legal_actions(self):
        actions = np.array([1, 0, 1, 1, 0, 1, 0])  # cols 0, 2, 3, 5
        session = make_session()
        session.states[-1].available_actions = actions
        assert session.legal_actions == [0, 2, 3, 5]

    def test_current_state(self):
        state1 = make_game_state(player=-1)
        state2 = make_game_state(player=1)
        session = GameSession(states=[state1, state2])
        assert session.current_state is state2


class TestEvalCaching:
    def test_cached_eval_starts_none(self):
        session = make_session()
        assert session._cached_eval is None

    def test_cached_eval_cleared_on_set(self):
        session = make_session()
        session._cached_eval = make_eval_result()
        assert session._cached_eval is not None
        session._cached_eval = None
        assert session._cached_eval is None

    def test_eval_history_starts_empty(self):
        session = make_session()
        assert session._eval_history == {}

    def test_eval_history_stores_by_move_number(self):
        session = make_session(move_history=[3, 4])
        result = make_eval_result()
        session._eval_history[session.move_number] = result
        assert session._eval_history[2] is result
