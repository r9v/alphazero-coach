"""Shared fixtures for tests."""

from dataclasses import dataclass, field
from unittest.mock import MagicMock

import numpy as np
import pytest

from core.engine import MoveStats, EvalResult, GameSession


def empty_board():
    """6x7 board of zeros."""
    return [[0] * 7 for _ in range(6)]


def make_game_state(board=None, player=-1, terminal=False, terminal_value=0, available_actions=None):
    """Create a mock game state object."""
    if board is None:
        board = np.array(empty_board())
    elif isinstance(board, list):
        board = np.array(board)
    if available_actions is None:
        available_actions = np.ones(7)

    state = MagicMock()
    state.board = board
    state.player = player
    state.terminal = terminal
    state.terminal_value = terminal_value
    state.available_actions = available_actions
    return state


def make_session(board=None, player=-1, terminal=False, terminal_value=0, move_history=None):
    """Create a GameSession with a mock state."""
    state = make_game_state(board, player, terminal, terminal_value)
    session = GameSession(states=[state], move_history=move_history or [])
    return session


def make_move_stats(column, visits, q_value, prior, visit_share):
    return MoveStats(column=column, visits=visits, q_value=q_value, prior=prior, visit_share=visit_share)


def make_eval_result(best_action=3, root_value=0.5, total_simulations=400, move_stats=None):
    if move_stats is None:
        move_stats = [
            make_move_stats(3, 300, 0.5, 0.6, 0.75),
            make_move_stats(4, 80, 0.1, 0.2, 0.20),
            make_move_stats(2, 20, -0.3, 0.1, 0.05),
        ]
    return EvalResult(
        best_action=best_action,
        root_value=root_value,
        total_simulations=total_simulations,
        move_stats=move_stats,
    )
