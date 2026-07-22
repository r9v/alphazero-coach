.PHONY: serve frontend test eval eval-judge mcp

# Run the FastAPI backend (serves the built frontend if frontend/dist exists)
serve:
	uvicorn core.api.server:app --reload

# Run the Vite dev server
frontend:
	cd frontend && npm install && npm run dev

# Backend test suite
test:
	pytest -q

# Retrieval eval against the golden set (no API key required)
eval:
	python -m core.eval.run

# Full eval incl. LLM-as-judge on generated answers (needs an LLM API key)
eval-judge:
	python -m core.eval.run --judge

# Start the MCP server (exposes engine + strategy tools over stdio)
mcp:
	python -m core.mcp.server
