"""FastAPI application with engine lifecycle management."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(_env_path, override=True)

from core.api.routes import router, set_engine
from core.api.coach_routes import coach_router, set_coach
from core.engine import Engine
from core.agent.coach import Coach


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[server] Loading AlphaZero engine...")
    engine = Engine()
    set_engine(engine)
    print("[server] Loading coaching agent...")
    coach = Coach(engine)
    set_coach(coach)
    print("[server] Ready.")
    yield
    print("[server] Shutting down.")


app = FastAPI(
    title="AlphaZero Coach",
    description="AI-powered Connect 4 coaching API",
    version="0.1.0",
    lifespan=lifespan,
)

# The API is same-origin in production (FastAPI serves the built SPA) and needs
# cross-origin access only for the Vite dev server. Restrict to a configurable
# allowlist; credentials are off since the API uses no cookies or auth (and the
# wildcard-origin + credentials combination is rejected by browsers anyway).
_DEFAULT_ORIGINS = "http://localhost:5173,http://localhost:8000,https://alphazero-coach.xyz"
_allowed_origins = [
    o.strip() for o in os.environ.get("ALLOWED_ORIGINS", _DEFAULT_ORIGINS).split(",") if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(router)
app.include_router(coach_router)


@app.get("/health")
def health():
    return {"status": "ok"}


# Serve built frontend in production (when frontend/dist exists)
_frontend_dist = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if _frontend_dist.is_dir():
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="assets")

    @app.get("/{path:path}")
    def serve_spa(path: str):
        """Serve the React SPA for any non-API route."""
        file = _frontend_dist / path
        if file.is_file():
            return FileResponse(file)
        return FileResponse(_frontend_dist / "index.html")
