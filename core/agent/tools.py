"""MCTS-backed tools that the coaching agent can call."""

from langchain_core.tools import tool

from core.engine import Engine
from core.agent.rag import StrategyKB


def _get_session_or_error(engine: Engine, game_id: str):
    """Look up a game session, returning (session, None) or (None, error_string)."""
    session = engine.get_session(game_id)
    if session is None:
        return None, "Error: game not found"
    return session, None


def _format_move_table(move_stats) -> list[str]:
    """Format move stats as an aligned text table."""
    lines = [f"  {'Col':>3}  {'Visits':>7}  {'Share':>6}  {'Q-value':>8}  {'Prior':>6}"]
    for m in move_stats:
        lines.append(
            f"  C{m.column:>2}  {m.visits:>7}  {m.visit_share:>5.1%}  {m.q_value:>+8.3f}  {m.prior:>5.1%}"
        )
    return lines


def _q_label(q_value: float) -> str:
    """Human-readable label for a Q-value."""
    q_pct = q_value * 100
    return "winning" if q_pct > 5 else "losing" if q_pct < -5 else "roughly equal"


def _find_threats(board) -> list[str]:
    """Find all 3-in-a-row with a playable empty 4th square."""
    rows, cols = 6, 7
    threats = []
    names = {-1: "Red", 1: "Yellow"}

    def is_playable(r, c):
        """Check if (r, c) is empty and either on the bottom row or has a piece below."""
        if r < 0 or r >= rows or c < 0 or c >= cols:
            return False
        return board[r][c] == 0 and (r == 0 or board[r - 1][c] != 0)

    # Directions: horizontal, vertical, both diagonals
    directions = [(0, 1), (1, 0), (1, 1), (1, -1)]

    for r in range(rows):
        for c in range(cols):
            for dr, dc in directions:
                # Check if 4 cells are in bounds
                cells = [(r + dr * i, c + dc * i) for i in range(4)]
                if any(cr < 0 or cr >= rows or cc < 0 or cc >= cols for cr, cc in cells):
                    continue

                values = [board[cr][cc] for cr, cc in cells]
                for player in [-1, 1]:
                    count = values.count(player)
                    empties = [(cr, cc) for (cr, cc), v in zip(cells, values) if v == 0]
                    if count == 3 and len(empties) == 1:
                        er, ec = empties[0]
                        if is_playable(er, ec):
                            direction = {(0,1): "horizontal", (1,0): "vertical",
                                        (1,1): "diagonal ↗", (1,-1): "diagonal ↘"}[(dr, dc)]
                            threats.append(
                                f"{names[player]} can win at column {ec} (row {er}) — "
                                f"{direction} threat"
                            )

    # Deduplicate
    return list(dict.fromkeys(threats))


def make_tools(engine: Engine, kb: StrategyKB | None = None):
    """Create tool functions bound to the given engine and knowledge base."""

    @tool
    def evaluate_position(game_id: str) -> str:
        """Evaluate the current board position using MCTS search.
        Returns the best move, win/draw/loss estimate, and per-column statistics
        including visit counts, Q-values, and network priors."""
        session, err = _get_session_or_error(engine, game_id)
        if err:
            return err
        result = engine.evaluate(session)

        lines = [
            f"Position evaluation ({result.total_simulations} MCTS simulations):",
            f"  Best move: Column {result.best_action}",
            f"  Position value: {result.root_value:+.3f} (from AI's perspective, +1 = winning, -1 = losing)",
            "",
            "  Per-column breakdown:",
            *_format_move_table(result.move_stats),
        ]

        return "\n".join(lines)

    @tool
    def get_best_moves(game_id: str, top_k: int = 3) -> str:
        """Get the top-K best moves ranked by MCTS visit count.
        Each move includes visit share, Q-value (expected outcome),
        and neural network prior probability."""
        session, err = _get_session_or_error(engine, game_id)
        if err:
            return err
        result = engine.evaluate(session)
        top = result.move_stats[:top_k]

        lines = [f"Top {len(top)} moves ({result.total_simulations} simulations):"]
        for i, m in enumerate(top, 1):
            lines.append(
                f"  {i}. Column {m.column} — {m.visit_share:.0%} of search visits, "
                f"Q-value {m.q_value:+.3f} ({_q_label(m.q_value)}), network prior {m.prior:.1%}"
            )

        return "\n".join(lines)

    @tool
    def compare_moves(game_id: str, column_a: int, column_b: int) -> str:
        """Compare two candidate moves side-by-side.
        Shows which column MCTS prefers and why (visit count, Q-value, prior)."""
        session, err = _get_session_or_error(engine, game_id)
        if err:
            return err
        result = engine.evaluate(session)
        stats = {m.column: m for m in result.move_stats}

        a = stats.get(column_a)
        b = stats.get(column_b)

        if a is None and b is None:
            return f"Neither column {column_a} nor {column_b} is a legal move."
        if a is None:
            return f"Column {column_a} is not a legal move. Column {column_b} has Q={b.q_value:+.3f}."
        if b is None:
            return f"Column {column_b} is not a legal move. Column {column_a} has Q={a.q_value:+.3f}."

        better = a if a.visits > b.visits else b
        worse = b if better is a else a
        diff = abs(a.q_value - b.q_value) * 100

        lines = [
            f"Comparing Column {column_a} vs Column {column_b}:",
            f"",
            f"  Column {a.column}: {a.visits} visits ({a.visit_share:.0%}), Q={a.q_value:+.3f}, prior={a.prior:.1%}",
            f"  Column {b.column}: {b.visits} visits ({b.visit_share:.0%}), Q={b.q_value:+.3f}, prior={b.prior:.1%}",
            f"",
            f"  MCTS prefers Column {better.column} by {diff:.1f} percentage points.",
        ]

        if diff < 2:
            lines.append("  The moves are very close — either is reasonable.")
        elif diff < 10:
            lines.append(f"  Column {better.column} is moderately better.")
        else:
            lines.append(f"  Column {better.column} is significantly better — Column {worse.column} is a clear mistake.")

        return "\n".join(lines)

    @tool
    def analyze_game(game_id: str) -> str:
        """Analyze the full game move-by-move.
        Replays all moves, evaluates each position, and identifies
        the critical turning point (biggest evaluation swing)."""
        session, err = _get_session_or_error(engine, game_id)
        if err:
            return err

        if len(session.move_history) < 2:
            return "Not enough moves to analyze. Play a few more moves first."

        # Replay through states and evaluate each
        import numpy as np
        game = engine.game
        state = game.new_game()
        evals = []

        for i, move in enumerate(session.move_history):
            pi = engine.mcts.get_policy(400, state)  # fewer sims for game replay speed
            root = engine.mcts.last_root
            best = int(np.argmax(pi))
            evals.append({
                "move_num": i + 1,
                "played": move,
                "best": best,
                "value": float(root.nnet_value),
                "was_best": move == best,
            })
            state = game.step(state, move)

        # Find biggest swing
        max_swing = 0
        critical_idx = 0
        for i in range(1, len(evals)):
            swing = abs(evals[i]["value"] - evals[i - 1]["value"])
            if swing > max_swing:
                max_swing = swing
                critical_idx = i

        lines = [
            f"Game analysis ({len(session.move_history)} moves):",
            "",
        ]

        for e in evals:
            marker = "" if e["was_best"] else f" (best was C{e['best']})"
            player = "Red" if e["move_num"] % 2 == 1 else "Yellow"
            lines.append(
                f"  Move {e['move_num']} ({player}): Column {e['played']}{marker} — eval {e['value']:+.3f}"
            )

        c = evals[critical_idx]
        lines.append("")
        lines.append(
            f"  Critical moment: Move {c['move_num']} — eval swung by {max_swing:.3f}"
        )

        if session.is_terminal:
            if session.winner == -1:
                lines.append("  Result: Red wins.")
            elif session.winner == 1:
                lines.append("  Result: Yellow wins.")
            else:
                lines.append("  Result: Draw.")

        return "\n".join(lines)

    @tool
    def get_game_state(game_id: str) -> str:
        """Get the current board state, whose turn it is, move history,
        and whether the game is over."""
        session, err = _get_session_or_error(engine, game_id)
        if err:
            return err
        board = session.current_state.board
        symbols = {0: ".", -1: "X", 1: "O"}
        lines = ["Current board (X=Red/You, O=Yellow/AI):"]
        lines.append("  Col:  0 1 2 3 4 5 6")
        for r in range(5, -1, -1):
            row = " ".join(symbols[board[r][c]] for c in range(7))
            lines.append(f"  Row {r}: {row}")
        lines.append("")

        # Describe each column's contents explicitly
        for c in range(7):
            pieces = []
            for r in range(6):
                if board[r][c] != 0:
                    who = "Red" if board[r][c] == -1 else "Yellow"
                    pieces.append(f"{who}@row{r}")
            count = len(pieces)
            remaining = 6 - count
            status = "FULL" if remaining == 0 else f"{remaining} slots left"
            if pieces:
                lines.append(f"  Column {c} ({status}): {', '.join(pieces)}")
            else:
                lines.append(f"  Column {c} (empty)")
        lines.append("")

        player = "Red (You)" if session.player == -1 else "Yellow (AI)"
        lines.append(f"  Turn: {player}")
        lines.append(f"  Move: {session.move_number}")

        # Show move history with player labels
        history_parts = []
        for i, col in enumerate(session.move_history):
            who = "Red" if i % 2 == 0 else "Yellow"
            history_parts.append(f"{i+1}. {who} → C{col}")
        lines.append(f"  History: {', '.join(history_parts) or 'none'}")

        if session.is_terminal:
            if session.winner == -1:
                lines.append("  Game over: Red wins!")
            elif session.winner == 1:
                lines.append("  Game over: Yellow wins!")
            else:
                lines.append("  Game over: Draw!")
        else:
            # Scan for threats (3-in-a-row with playable empty 4th)
            threats = _find_threats(board)
            if threats:
                lines.append("")
                lines.append("  Active threats:")
                for t in threats:
                    lines.append(f"    {t}")
            else:
                lines.append("")
                lines.append("  No immediate threats for either side.")

        return "\n".join(lines)

    @tool
    def search_strategy(query: str) -> str:
        """Search the Connect 4 strategy knowledge base for concepts related to the query.
        Use this to find expert strategy information about topics like center control,
        odd/even threat theory, double threats, tempo, openings, or tactical patterns.
        Returns relevant strategy excerpts with source citations."""
        if kb is None:
            return "Strategy knowledge base not available."

        hits = kb.search(query, n_results=3)
        if not hits:
            return "No relevant strategy content found."

        lines = ["Strategy knowledge base results:"]
        for i, hit in enumerate(hits, 1):
            lines.append(f"\n--- Source: {hit['source']} ({hit['section']}) ---")
            lines.append(hit["content"])

        return "\n".join(lines)

    @tool
    def evaluate_last_move(game_id: str) -> str:
        """Evaluate whether the player's last move was good or bad.
        Compares what the player actually played vs what the engine would have recommended.
        Only works when there are at least 2 moves (player + AI response)."""
        import numpy as np
        session, err = _get_session_or_error(engine, game_id)
        if err:
            return err

        if len(session.move_history) < 2:
            return "Not enough moves to evaluate."

        # Find the player's last move (second-to-last in history, since AI moved last)
        player_move = session.move_history[-2]
        move_num = len(session.move_history) - 1  # 1-indexed

        # Replay to the position BEFORE the player's move and evaluate
        game_obj = engine.game
        state = game_obj.new_game()
        for m in session.move_history[:-2]:
            state = game_obj.step(state, m)

        pi = engine.mcts.get_policy(400, state)
        best_action = int(np.argmax(pi))
        root = engine.mcts.last_root

        played_child = root.children[player_move]
        best_child = root.children[best_action]

        played_q = float(played_child.Q) if played_child else 0
        best_q = float(best_child.Q) if best_child else 0
        diff = abs(best_q - played_q) * 100

        if player_move == best_action:
            return f"Your move (column {player_move}) was the engine's top choice! Well played."
        elif diff < 3:
            return (
                f"Your move (column {player_move}) was fine — nearly as good as the engine's "
                f"top pick (column {best_action}). Difference is negligible ({diff:.1f}%)."
            )
        elif diff < 10:
            return (
                f"Your move (column {player_move}) was okay but not optimal. "
                f"The engine preferred column {best_action} (Q-diff: {diff:.1f}%). "
                f"Column {best_action} had {int(pi[best_action]*100)}% of visits vs "
                f"your column {player_move} at {int(pi[player_move]*100)}%."
            )
        else:
            return (
                f"Your move (column {player_move}) was a mistake. "
                f"The engine strongly preferred column {best_action} (Q-diff: {diff:.1f}%). "
                f"Column {best_action} had {int(pi[best_action]*100)}% of visits vs "
                f"your column {player_move} at {int(pi[player_move]*100)}%."
            )

    tools = [evaluate_position, get_best_moves, compare_moves, analyze_game,
             get_game_state, search_strategy, evaluate_last_move]
    return tools
