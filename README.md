# AlphaZero Coach

AI-powered Connect 4 coaching platform. Play against a superhuman AlphaZero agent in the browser while an LLM coach analyzes positions in real time — powered by Monte Carlo Tree Search evaluation and a strategy knowledge base.

Built on top of [alphazero-boardgames](https://github.com/r9v/alphazero-boardgames), my from-scratch AlphaZero implementation with Cython-accelerated MCTS, PyTorch neural network, and bitboard game engine. The Connect 4 model was trained via self-play and defeated 2200 Elo bots.

## Features

- **Play against AlphaZero** — interactive Connect 4 board with animated piece drops and hover previews
- **Live coaching** — after each move, an LLM agent evaluates the position via MCTS and streams natural-language analysis
- **MCTS analysis panel** — visual breakdown of the AI's thinking: visit counts, Q-values, and network priors per column
- **Conversational Q&A** — ask the coach anything: "Why is column 4 better than column 3?"
- **Strategy knowledge base (RAG)** — coach cites Connect 4 concepts (center control, odd/even theory, threats, tempo) from an indexed corpus via ChromaDB
- **Post-game review** — full game replay identifying the critical turning point (biggest evaluation swing)

## Architecture

```
React Frontend (Vite + TypeScript + Tailwind)
├── Interactive board (play against AlphaZero)
├── AI Coach chat panel (SSE streaming, Q&A)
└── MCTS analysis panel (bar charts, Q-values)
        │
        │ REST + SSE
        ▼
FastAPI Backend
├── Game engine — MCTS evaluation, step/undo, game state
├── LLM Agent (LangGraph) with tools:
│   ├── evaluate_position  →  MCTS Q-values + win/draw/loss probs
│   ├── get_best_moves     →  top-K moves with visit counts + priors
│   ├── compare_moves      →  side-by-side move comparison
│   ├── analyze_game       →  full replay + critical moment detection
│   ├── get_game_state     →  board state as text
│   └── search_strategy    →  RAG search over strategy corpus
└── RAG pipeline — ChromaDB + sentence-transformers embeddings
```

## Tech Stack

- **Backend:** Python, FastAPI, LangChain/LangGraph, ChromaDB, sentence-transformers
- **Frontend:** React, TypeScript, Vite, Tailwind CSS
- **Game engine:** [alphazero-boardgames](https://github.com/r9v/alphazero-boardgames) (PyTorch, Cython MCTS, bitboard engine)
- **LLM:** Google Gemini or Anthropic Claude (auto-detected from API key)

## Prerequisites

- Python 3.10+
- Node.js 18+
- A C compiler (MSVC on Windows, gcc on Linux) — required for Cython extensions in alphazero-boardgames
- An LLM API key — either [Google AI](https://aistudio.google.com/) (free tier) or [Anthropic](https://console.anthropic.com/)

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
# Edit .env with your API key (GOOGLE_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY)

# Start the backend
uvicorn core.api.server:app --reload

# In a second terminal, start the frontend
cd frontend
npm install
npm run dev

# Open http://localhost:5173
```

## How It Works

1. You play a move on the board (Red pieces)
2. The AlphaZero engine responds via 200 MCTS simulations (Yellow pieces)
3. The MCTS analysis panel shows visit counts and Q-values for each column
4. The LLM coaching agent receives the game state, calls MCTS tools to evaluate the position, optionally searches the strategy knowledge base, and streams a natural-language explanation of what's happening

The coach uses a ReAct agent loop — it decides which tools to call based on the situation, gets real data from the engine, then interprets it for the human player.

## License

MIT
