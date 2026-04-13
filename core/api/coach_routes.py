"""SSE streaming routes for the coaching agent."""

import json

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.agent.coach import Coach

coach_router = APIRouter(prefix="/coach", tags=["coach"])

_coach: Coach | None = None


def set_coach(coach: Coach) -> None:
    global _coach
    _coach = coach


def _get_coach() -> Coach:
    if _coach is None:
        raise HTTPException(503, "Coach not initialized")
    return _coach


class ChatRequest(BaseModel):
    message: str


async def _sse_stream(generator):
    """Wrap an async generator into SSE format."""
    try:
        async for chunk in generator:
            data = json.dumps({"type": "token", "content": chunk})
            yield f"data: {data}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"


@coach_router.post("/{game_id}/chat")
async def chat(game_id: str, req: ChatRequest, request: Request):
    """Stream a coach response in the game's conversation."""
    coach = _get_coach()
    user_ip = request.client.host if request.client else "unknown"
    return StreamingResponse(
        _sse_stream(coach.chat(game_id, req.message, user_id=user_ip)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
