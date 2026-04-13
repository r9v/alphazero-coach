"""LLM coaching agent that uses MCTS tools to analyze Connect 4 games."""

import os
from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

# Langfuse observability (optional — only active if env vars are set)
_langfuse_handler = None
if os.environ.get("LANGFUSE_SECRET_KEY"):
    try:
        from langfuse.langchain import CallbackHandler
        _langfuse_handler = CallbackHandler()
        print("[coach] Langfuse tracing enabled")
    except ImportError:
        print("[coach] Langfuse not installed, skipping tracing")

MAX_HISTORY = 50

from core.agent.tools import make_tools
from core.agent.rag import StrategyKB
from core.engine import Engine


def _make_llm(temperature: float = 0.15):
    """Create an LLM instance based on available API keys.

    Checks env vars in order: GOOGLE_API_KEY, ANTHROPIC_API_KEY.
    """
    if os.environ.get("GOOGLE_API_KEY"):
        from langchain_google_genai import ChatGoogleGenerativeAI
        model = os.environ.get("LLM_MODEL", "gemini-2.5-flash")
        print(f"[coach] Using Google Gemini: {model}")
        return ChatGoogleGenerativeAI(model=model, temperature=temperature)

    if os.environ.get("ANTHROPIC_API_KEY"):
        from langchain_anthropic import ChatAnthropic
        model = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")
        print(f"[coach] Using Anthropic Claude: {model}")
        return ChatAnthropic(model=model, temperature=temperature)

    raise RuntimeError(
        "No LLM API key found. Set one of: GOOGLE_API_KEY, ANTHROPIC_API_KEY"
    )

SYSTEM_PROMPT = """You're a friendly, sharp Connect 4 coach watching a game in real time.
A player (Red, plays first) is up against a tough AlphaZero AI (Yellow). You're sitting
next to them, helping them see what's really going on in the position.

== HOW TO THINK ==
- NEVER output ANY text before calling tools. Call tools FIRST, then respond.
- ALWAYS call tools first to analyze the position. Never guess.
- ALWAYS recommend the move with the most MCTS visits. That is the engine's recommendation.
  Only mention alternative moves if they are close in visit share (within ~10% of the top move).
- Q-values are from the AI's perspective: positive = AI winning, negative = player winning.
  Use Q-values to explain WHY a move is good or bad, not to override the visit-count ranking.
- ONLY state facts visible in tool output. Never invent threats not listed in "Active threats".

== WHICH TOOLS TO USE ==
For every auto-analysis after a move, call ALL THREE of these together:
  1. evaluate_last_move — grade the player's last move FIRST, so you can praise or coach
  2. get_game_state — see the board and active threats
  3. get_best_moves — find the strongest next move to recommend

Additionally:
- Call search_strategy when a strategic concept is relevant (center control, double threats,
  odd/even theory, tempo, etc.). Work the concept into your advice naturally.
  Use this at least every few moves — don't just recommend moves, teach strategy.
- Call compare_moves when two moves are close and worth discussing the tradeoff.
- Call analyze_game when the game is over to identify the turning point.

== HOW TO TALK ==
Tool outputs are your private analysis notes — the player never sees them.
Your job is to translate engine analysis into what's happening ON THE BOARD.

NEVER mention or reference:
- Visit counts, visit percentages, or simulation numbers
- Q-values, evaluation scores, or numerical confidence
- "The engine", "MCTS", "search", "neural network", or "prior"
- Percentage signs or decimal scores of any kind

INSTEAD talk about:
- What you SEE: threats, patterns, diagonals, stacks, open lanes, blocking needs
- WHY a move matters: "that connects your diagonal", "they can't answer both threats"
- Strategic concepts by name: center control, tempo, double threat, odd/even theory

TONE:
- 1-2 sentences for routine moves. 3 max for critical moments.
- Match your energy to the position — excited when winning, cautionary when close,
  encouraging after mistakes. Don't be monotone.
- Vary how you start. Not every message should open with "Play column X."
- Don't recap moves or board state — the player can see the board.
- When the player blunders, be constructive, not condescending.

== EXAMPLES ==

BAD: "Play column 2. The engine is 93% confident and Q-value is +0.708.
This seizes center control."

GOOD: "Column 2 — you'll have three in a row with room to extend both ways.
Hard for Yellow to answer that."

BAD: "Column 4 is your move. The engine has 100% confidence with a
Q-value of +0.947. The AI's last move was a blunder."

GOOD: "They just handed you column 4. That connects your diagonal —
game's almost over."

BAD: "Your move (column 5) was okay but not optimal. The engine preferred
column 3 (Q-diff: 8.2%). Column 3 had 74% of visits vs your column at 12%."

GOOD: "Column 5 works, but column 3 would've been sneaky — it sets up
a double threat they can't block both sides of."
"""


class Coach:
    """Streaming coaching agent backed by LLM + MCTS tools."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.kb = StrategyKB()
        tools = make_tools(engine, self.kb)
        llm = _make_llm()
        self.agent = create_react_agent(llm, tools)
        self._history: dict[str, list] = {}

    async def chat(self, game_id: str, message: str, user_id: str | None = None) -> AsyncIterator[str]:
        """Send a message in the game's conversation, stream the response."""
        if game_id not in self._history:
            self._history[game_id] = []
        history = self._history[game_id]

        history.append(HumanMessage(content=message))

        # Keep all user messages but only the last coach response to force fresh tool calls
        last_ai = next((i for i in range(len(history) - 1, -1, -1) if isinstance(history[i], AIMessage)), None)
        recent = [msg for i, msg in enumerate(history) if not isinstance(msg, AIMessage) or i == last_ai]

        system = SYSTEM_PROMPT + f"\n\nThe current game ID is: {game_id}. Always use this game_id when calling tools."
        messages = [SystemMessage(content=system)] + recent[-MAX_HISTORY:]

        full_response = ""
        tools_ever_completed = False
        pending_tools = 0
        buffered_text = ""

        config = {}
        if _langfuse_handler:
            config["callbacks"] = [CallbackHandler()]

        # Wrap in Langfuse session + user context if available
        ctx = None
        if _langfuse_handler:
            from langfuse import propagate_attributes
            ctx = propagate_attributes(session_id=game_id, user_id=user_id)
            ctx.__enter__()

        try:
            async for event in self.agent.astream_events(
                {"messages": messages},
                version="v2",
                config=config,
            ):
                kind = event["event"]

                if kind == "on_tool_start":
                    pending_tools += 1

                elif kind == "on_tool_end":
                    pending_tools -= 1
                    if pending_tools <= 0:
                        tools_ever_completed = True
                        buffered_text = ""

                elif kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        content = chunk.content
                        if isinstance(content, str):
                            text_chunk = content
                        elif isinstance(content, list):
                            text_chunk = "".join(
                                item.get("text", "") if isinstance(item, dict) else str(item)
                                for item in content
                            )
                        else:
                            text_chunk = ""

                        if text_chunk:
                            if not tools_ever_completed or pending_tools > 0:
                                buffered_text += text_chunk
                            else:
                                full_response += text_chunk
                                yield text_chunk
        finally:
            if ctx:
                ctx.__exit__(None, None, None)

        if full_response:
            history.append(AIMessage(content=full_response))
