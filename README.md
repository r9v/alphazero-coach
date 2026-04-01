# AlphaZero Coach

AI-powered Connect 4 coach that analyzes positions, explains strategy, and reviews your games move by move. Built on top of [alphazero-boardgames](https://github.com/r9v/alphazero-boardgames) — a from-scratch AlphaZero implementation with Cython-accelerated MCTS and bitboard game engine.

You play Connect 4 against a superhuman AlphaZero agent in the browser. A coaching agent watches the game in real time, evaluates positions by calling MCTS as a tool, and streams natural-language analysis explaining why moves are good or bad — with citations from a strategy knowledge base.

## Features

- **Live coaching** — real-time position analysis streamed as you play, powered by MCTS evaluation + LLM interpretation
- **Post-game review** — move-by-move breakdown identifying the critical turning point (biggest win-probability swing)
- **Conversational Q&A** — ask the coach about any position: "Why is column 4 better than column 3?"
- **Strategy knowledge base (RAG)** — coach cites Connect 4 strategy concepts (threats, tempo, odd/even theory) from an indexed corpus
- **Game history** — past games and conversations persisted in SQLite, resumable across sessions
- **Observability** — full LLM agent traces (tool calls, reasoning, latency) via Langfuse

## Architecture

```
React Frontend (Vite + Tailwind)
├── Interactive board (play against AlphaZero)
└── Coach chat panel (streaming SSE, conversation history, source citations)
        │
        │ REST + SSE
        ▼
FastAPI Backend
├── Game engine — MCTS evaluation, step/undo, game state management
├── Agent — LLM orchestrator with tools:
│   ├── evaluate_position  →  runs MCTS, returns Q-values + win/draw/loss probs
│   ├── get_best_moves     →  top-K moves with visit counts + network prior
│   ├── compare_moves      →  side-by-side evaluation of two candidate moves
│   ├── analyze_game       →  full game replay with critical moment detection
│   └── search_strategy    →  RAG search over strategy corpus
├── SQLite — game logs + chat history
└── Langfuse — LLM call tracing + tool use spans
```

## Tech Stack

- **Backend:** FastAPI, LangChain/LangGraph, SQLite, Langfuse
- **Frontend:** React, TypeScript, Vite, Tailwind CSS
- **Game engine:** [alphazero-boardgames](https://github.com/r9v/alphazero-boardgames) (PyTorch, Cython MCTS, bitboard engine)
- **LLM:** Anthropic Claude (via API)

## Prerequisites

- Python 3.10+
- Node.js 18+
- A C compiler (MSVC on Windows, gcc on Linux) — required to build the Cython extensions in alphazero-boardgames
- An Anthropic API key
- (Optional) Langfuse account for observability

## Setup

```bash
# Clone both repos
git clone https://github.com/r9v/alphazero-boardgames.git
git clone https://github.com/r9v/alphazero-coach.git

# Install the game engine (builds Cython extensions)
cd alphazero-boardgames
pip install -e .
cd ..

# Install the coach
cd alphazero-coach
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your ANTHROPIC_API_KEY (and optionally LANGFUSE_* keys)

# Start the backend
uvicorn core.api.server:app --reload

# In a second terminal, start the frontend
cd frontend
npm install
npm run dev

# Open http://localhost:5173
```

## Project Structure

```
alphazero-coach/
├── core/
│   ├── api/            # FastAPI app (routes, models, SSE streaming)
│   ├── agent/          # LLM agent, tools (MCTS wrappers), RAG pipeline
│   └── db.py           # SQLite — game logs + chat history
├── frontend/           # React app (board + chat panel)
├── data/
│   └── strategy/       # RAG corpus (Connect 4 strategy documents)
├── requirements.txt
└── README.md
```

## License

MIT
