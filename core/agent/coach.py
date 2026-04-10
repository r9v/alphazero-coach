"""LLM coaching agent that uses MCTS tools to analyze Connect 4 games."""

import os
from collections.abc import AsyncIterator

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

from core.agent.tools import make_tools
from core.agent.rag import StrategyKB
from core.engine import Engine


def _make_llm(temperature: float = 0.3):
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
        model = os.environ.get("LLM_MODEL", "claude-sonnet-4-20250514")
        print(f"[coach] Using Anthropic Claude: {model}")
        return ChatAnthropic(model=model, temperature=temperature)

    raise RuntimeError(
        "No LLM API key found. Set one of: GOOGLE_API_KEY, ANTHROPIC_API_KEY"
    )

SYSTEM_PROMPT = """You are an expert Connect 4 coach powered by a superhuman AlphaZero engine.

You're coaching a player (Red, plays first) against an AlphaZero AI (Yellow).
Talk directly to the player — say "you" not "the human" or "Red". Be like a friendly coach
sitting next to them, not a commentator describing the game in third person.

Guidelines:
- Use your tools to evaluate positions before giving advice. Don't guess.
- Explain WHY moves are good or bad — reference threats, tempo, center control, blocking.
- Be concise but insightful. 2-3 sentences per analysis, not an essay.
- When the player makes a suboptimal move, explain what was better without being condescending.
- Reference specific columns by number (0-6, left to right).
- The move with the most MCTS visits is the strongest move. Visit share is the primary signal
  for move quality — Q-values are secondary confirmation.
- Q-values are from the AI's perspective: positive = AI winning, negative = you winning.
  Translate this naturally — don't show raw Q-values, say things like "you're ahead" or "this is tight".
- Don't repeat the same analysis structure every time. Vary your commentary.
- Use search_strategy to look up Connect 4 concepts (center control, odd/even theory, double threats,
  tempo, openings) when they're relevant. Cite the concept by name.
"""


class Coach:
    """Streaming coaching agent backed by LLM + MCTS tools."""

    def __init__(self, engine: Engine):
        self.engine = engine
        self.kb = StrategyKB()
        tools = make_tools(engine, self.kb)
        llm = _make_llm()
        self.agent = create_react_agent(llm, tools)

    async def analyze_move(self, game_id: str) -> AsyncIterator[str]:
        """Stream analysis of the current position after a move."""
        session = self.engine.get_session(game_id)
        if session is None:
            yield "Game not found."
            return

        last_move = session.move_history[-1] if session.move_history else None
        move_num = session.move_number

        if session.is_terminal:
            prompt = (
                f"The game is over (move {move_num}). "
                f"Analyze the game and explain the result. "
                f"What was the critical turning point?"
            )
        else:
            prompt = (
                f"The human just played and the AI responded. We're at move {move_num}. "
                f"AI's last move was column {last_move}. "
                f"Evaluate the current position and briefly explain what's happening. "
                f"Is the human in good shape or trouble? Any threats to watch out for?"
            )

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"[Game ID: {game_id}]\n\n{prompt}"),
        ]

        async for event in self.agent.astream_events(
            {"messages": messages},
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield chunk.content

    async def ask(self, game_id: str, question: str) -> AsyncIterator[str]:
        """Stream a response to a user question about the game."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"[Game ID: {game_id}]\n\n{question}"),
        ]

        async for event in self.agent.astream_events(
            {"messages": messages},
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    yield chunk.content
