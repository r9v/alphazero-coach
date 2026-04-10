"""LLM coaching agent that uses MCTS tools to analyze Connect 4 games."""

import os
from collections.abc import AsyncIterator

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent

MAX_HISTORY = 50

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
        model = os.environ.get("LLM_MODEL", "claude-haiku-4-5-20251001")
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
- The move with the most MCTS visits is usually the strongest, but ALWAYS check Q-values too.
  A move with fewer visits but a significantly better Q-value may be the actual best play.
  When visits and Q-values disagree, mention both options and explain the tradeoff.
- Q-values are from the AI's perspective: positive = AI winning, negative = you winning.
  Translate this naturally — don't show raw Q-values, say things like "you're ahead" or "this is tight".
- Don't repeat the same analysis structure every time. Vary your commentary.
- Use search_strategy to look up Connect 4 concepts when they're relevant. Cite the concept by name.
- NEVER output ANY text before calling tools. Call tools FIRST, then respond with analysis.
- Don't recap the game state or moves — the player can see the board. Jump straight into strategy.
- ONLY state facts visible in tool output. Never invent threats not listed in "Active threats".
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

    async def chat(self, game_id: str, message: str) -> AsyncIterator[str]:
        """Send a message in the game's conversation, stream the response."""
        if game_id not in self._history:
            self._history[game_id] = []
        history = self._history[game_id]

        history.append(HumanMessage(content=message))

        # Build messages: keep only user messages + last coach response to force fresh tool calls
        recent = []
        coach_count = 0
        for msg in reversed(history):
            if isinstance(msg, AIMessage):
                if coach_count >= 1:
                    continue  # skip older coach responses
                coach_count += 1
            recent.append(msg)
        recent.reverse()

        system = SYSTEM_PROMPT + f"\n\nThe current game ID is: {game_id}. Always use this game_id when calling tools."
        messages = [SystemMessage(content=system)] + recent[-MAX_HISTORY:]

        full_response = ""
        async for event in self.agent.astream_events(
            {"messages": messages},
            version="v2",
        ):
            if event["event"] == "on_chat_model_stream":
                chunk = event["data"].get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    content = chunk.content
                    if isinstance(content, str):
                        full_response += content
                        yield content
                    elif isinstance(content, list):
                        text = "".join(
                            item.get("text", "") if isinstance(item, dict) else str(item)
                            for item in content
                        )
                        if text:
                            full_response += text
                            yield text

        if full_response:
            history.append(AIMessage(content=full_response))
