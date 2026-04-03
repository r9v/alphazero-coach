"""MCTS-backed tools that the coaching agent can call."""

from langchain_core.tools import tool

from core.engine import Engine
from core.agent.rag import StrategyKB


def make_tools(engine: Engine, kb: StrategyKB | None = None):
    """Create tool functions bound to the given engine and knowledge base."""

    @tool
    def evaluate_position(game_id: str) -> str:
        """Evaluate the current board position using MCTS search.
        Returns the best move, win/draw/loss estimate, and per-column statistics
        including visit counts, Q-values, and network priors."""
        session = engine.get_session(game_id)
        if session is None:
            return "Error: game not found"

        result = engine.evaluate(session)

        lines = [
            f"Position evaluation ({result.total_simulations} MCTS simulations):",
            f"  Best move: Column {result.best_action}",
            f"  Position value: {result.root_value:+.3f} (from AI's perspective, +1 = winning, -1 = losing)",
            "",
            "  Per-column breakdown:",
            f"  {'Col':>3}  {'Visits':>7}  {'Share':>6}  {'Q-value':>8}  {'Prior':>6}",
        ]
        for m in result.move_stats:
            lines.append(
                f"  C{m.column:>2}  {m.visits:>7}  {m.visit_share:>5.1%}  {m.q_value:>+8.3f}  {m.prior:>5.1%}"
            )

        return "\n".join(lines)

    @tool
    def get_best_moves(game_id: str, top_k: int = 3) -> str:
        """Get the top-K best moves ranked by MCTS visit count.
        Each move includes visit share, Q-value (expected outcome),
        and neural network prior probability."""
        session = engine.get_session(game_id)
        if session is None:
            return "Error: game not found"

        result = engine.evaluate(session)
        top = result.move_stats[:top_k]

        lines = [f"Top {len(top)} moves ({result.total_simulations} simulations):"]
        for i, m in enumerate(top, 1):
            q_pct = m.q_value * 100
            label = "winning" if q_pct > 5 else "losing" if q_pct < -5 else "roughly equal"
            lines.append(
                f"  {i}. Column {m.column} — {m.visit_share:.0%} of search visits, "
                f"Q-value {m.q_value:+.3f} ({label}), network prior {m.prior:.1%}"
            )

        return "\n".join(lines)

    @tool
    def compare_moves(game_id: str, column_a: int, column_b: int) -> str:
        """Compare two candidate moves side-by-side.
        Shows which column MCTS prefers and why (visit count, Q-value, prior)."""
        session = engine.get_session(game_id)
        if session is None:
            return "Error: game not found"

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
        session = engine.get_session(game_id)
        if session is None:
            return "Error: game not found"

        if len(session.move_history) < 2:
            return "Not enough moves to analyze. Play a few more moves first."

        # Replay through states and evaluate each
        import numpy as np
        game = engine.game
        state = game.new_game()
        evals = []

        for i, move in enumerate(session.move_history):
            pi = engine.mcts.get_policy(100, state)  # fewer sims for speed
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
        session = engine.get_session(game_id)
        if session is None:
            return "Error: game not found"

        board = session.current_state.board
        symbols = {0: ".", -1: "X", 1: "O"}
        lines = ["Current board (X=Red/Human, O=Yellow/AI):"]
        for r in range(5, -1, -1):
            row = " ".join(symbols[board[r][c]] for c in range(7))
            lines.append(f"  {row}")
        lines.append("  0 1 2 3 4 5 6")
        lines.append("")

        player = "Red (Human)" if session.player == -1 else "Yellow (AI)"
        lines.append(f"  Turn: {player}")
        lines.append(f"  Move: {session.move_number}")
        lines.append(f"  History: {session.move_history}")

        if session.is_terminal:
            if session.winner == -1:
                lines.append("  Game over: Red wins!")
            elif session.winner == 1:
                lines.append("  Game over: Yellow wins!")
            else:
                lines.append("  Game over: Draw!")

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

    tools = [evaluate_position, get_best_moves, compare_moves, analyze_game, get_game_state, search_strategy]
    return tools
