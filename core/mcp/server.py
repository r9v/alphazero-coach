"""Model Context Protocol (MCP) server exposing the AlphaZero Coach engine.

Runs the same MCTS evaluation and strategy-retrieval tools the in-app coach uses,
but over MCP stdio — so any MCP client (Claude Desktop, an IDE agent, or another
orchestrator) can drive the Connect 4 engine and query the strategy knowledge
base directly. This mirrors the "MCP RAG server" pattern used to expose an
internal knowledge/tooling layer to external AI assistants.

Run:
    python -m core.mcp.server

Register with an MCP client by pointing it at that command over stdio.
"""

from mcp.server.fastmcp import FastMCP

from core.engine import Engine
from core.agent.rag import StrategyKB

mcp = FastMCP("alphazero-coach")

# Shared engine + knowledge base for the lifetime of the server process.
_engine = Engine()
_kb = StrategyKB()


@mcp.tool()
def new_game() -> str:
    """Start a new Connect 4 game. Returns the game_id to use in later calls."""
    import uuid
    game_id = uuid.uuid4().hex[:8]
    _engine.new_game(game_id)
    return f"Started game {game_id}. You are Red (you move first); AI is Yellow."


@mcp.tool()
def play_move(game_id: str, column: int) -> str:
    """Drop a piece in a column (0-6) for the human player, then let the AI reply."""
    try:
        _engine.player_move(game_id, column)
        session = _engine.get_session(game_id)
        if session and not session.is_terminal:
            _engine.ai_move(game_id)
    except (KeyError, ValueError) as e:
        return f"Error: {e}"
    session = _engine.get_session(game_id)
    if session is None:
        return "Error: game not found"
    return f"Board after moves {session.move_history}. Terminal={session.is_terminal}."


@mcp.tool()
def evaluate_position(game_id: str) -> str:
    """Run MCTS on the current position and return the best move and per-column stats."""
    session = _engine.get_session(game_id)
    if session is None:
        return "Error: game not found"
    if session.is_terminal:
        return "Game is over — nothing to evaluate."
    result = _engine.evaluate(session)
    lines = [
        f"Best move: column {result.best_action}",
        f"Position value (AI perspective): {result.root_value:+.3f}",
        f"Simulations: {result.total_simulations}",
    ]
    for m in result.move_stats[:5]:
        lines.append(f"  C{m.column}: {m.visit_share:.0%} visits, Q={m.q_value:+.3f}")
    return "\n".join(lines)


@mcp.tool()
def search_strategy(query: str, n_results: int = 3) -> str:
    """Search the Connect 4 strategy knowledge base (hybrid retrieval + rerank)."""
    hits = _kb.search(query, n_results=n_results)
    if not hits:
        return "No relevant strategy content found."
    out = []
    for hit in hits:
        out.append(f"--- {hit['source']} ({hit['section']}) ---\n{hit['content']}")
    return "\n\n".join(out)


if __name__ == "__main__":
    mcp.run()
