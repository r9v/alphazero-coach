"""FastAPI application with engine lifecycle management."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from dotenv import load_dotenv

load_dotenv()

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
