"""FastAPI application with engine lifecycle management."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.api.routes import router, set_engine
from core.engine import Engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[server] Loading AlphaZero engine...")
    engine = Engine()
    set_engine(engine)
    print("[server] Engine ready.")
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


@app.get("/health")
def health():
    return {"status": "ok"}
