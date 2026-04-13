"""Tests for MCTS tool helper functions."""

from core.agent.tools import _q_label, _format_move_table, _find_threats
from tests.conftest import make_move_stats, empty_board


class TestQLabel:
    def test_winning(self):
        assert _q_label(0.1) == "winning"
        assert _q_label(0.5) == "winning"
        assert _q_label(1.0) == "winning"

    def test_losing(self):
        assert _q_label(-0.1) == "losing"
        assert _q_label(-0.5) == "losing"
        assert _q_label(-1.0) == "losing"

    def test_roughly_equal(self):
        assert _q_label(0.0) == "roughly equal"
        assert _q_label(0.05) == "roughly equal"
        assert _q_label(-0.05) == "roughly equal"

    def test_boundaries(self):
        # Exactly at ±5% boundary
        assert _q_label(0.05) == "roughly equal"  # 5.0, not > 5
        assert _q_label(-0.05) == "roughly equal"  # -5.0, not < -5
        assert _q_label(0.051) == "winning"
        assert _q_label(-0.051) == "losing"


class TestFormatMoveTable:
    def test_single_move(self):
        stats = [make_move_stats(column=3, visits=400, q_value=0.5, prior=0.8, visit_share=1.0)]
        lines = _format_move_table(stats)
        assert len(lines) == 2  # header + 1 row
        assert "Col" in lines[0]
        assert "C 3" in lines[1]

    def test_multiple_moves(self):
        stats = [
            make_move_stats(3, 300, 0.5, 0.6, 0.75),
            make_move_stats(4, 80, 0.1, 0.2, 0.20),
            make_move_stats(2, 20, -0.3, 0.1, 0.05),
        ]
        lines = _format_move_table(stats)
        assert len(lines) == 4  # header + 3 rows

    def test_empty(self):
        lines = _format_move_table([])
        assert len(lines) == 1  # header only


class TestFindThreats:
    def test_empty_board(self):
        board = empty_board()
        assert _find_threats(board) == []

    def test_horizontal_threat(self):
        board = empty_board()
        # Red has 3 in a row on bottom: cols 1,2,3 — col 4 is playable
        board[0][1] = -1
        board[0][2] = -1
        board[0][3] = -1
        threats = _find_threats(board)
        assert any("Red" in t and "horizontal" in t for t in threats)

    def test_vertical_threat(self):
        board = empty_board()
        # Yellow has 3 stacked in col 3: rows 0,1,2 — row 3 is playable
        board[0][3] = 1
        board[1][3] = 1
        board[2][3] = 1
        threats = _find_threats(board)
        assert any("Yellow" in t and "vertical" in t for t in threats)

    def test_diagonal_threat(self):
        board = empty_board()
        # Red diagonal: (0,0), (1,1), (2,2) — need (3,3) playable
        board[0][0] = -1
        board[0][1] = 1   # support for (1,1)
        board[1][1] = -1
        board[0][2] = 1   # support for (2,2)
        board[1][2] = 1   # support
        board[2][2] = -1
        # (3,3) needs support at (2,3)
        board[0][3] = 1
        board[1][3] = 1
        board[2][3] = 1
        threats = _find_threats(board)
        assert any("Red" in t and "diagonal" in t for t in threats)

    def test_not_playable_threat(self):
        board = empty_board()
        # 3 in a row but the empty cell is NOT playable (no piece below it)
        board[0][1] = -1
        board[0][2] = -1
        board[0][3] = -1
        # col 0 row 0 is playable (bottom row), but col 4 row 0 is also playable
        # Let's make col 0 blocked: put the gap at row 1 with nothing below
        board2 = empty_board()
        board2[1][0] = -1
        board2[1][1] = -1
        board2[1][2] = -1
        # col 3 at row 1 needs support at row 0 — row 0 col 3 is empty, so not playable
        threats = _find_threats(board2)
        # The gap is at (1,3) which has no piece at (0,3) — not playable
        assert not any("column 3 (row 1)" in t for t in threats)

    def test_deduplication(self):
        board = empty_board()
        board[0][0] = -1
        board[0][1] = -1
        board[0][2] = -1
        threats = _find_threats(board)
        # Should not have duplicate entries
        assert len(threats) == len(set(threats))
