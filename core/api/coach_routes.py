"""SSE streaming routes for the coaching agent."""

import json
import os

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core.agent.coach import Coach
from core.api.ratelimit import SlidingWindowLimiter

coach_router = APIRouter(prefix="/coach", tags=["coach"])

# Each coach message triggers an LLM call, so throttle per client IP to protect
# the API budget on public demos (per hour; 0 = unlimited, for local dev).
MAX_COACH_MSGS = int(os.environ.get("MAX_COACH_MSGS", "0"))
_chat_limiter = SlidingWindowLimiter(MAX_COACH_MSGS, window_seconds=3600)

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
    from core.api.routes import _get_client_ip, _get_engine

    # Validate the game exists BEFORE invoking the LLM, so an unknown game_id
    # returns 404 instead of billing an LLM call for a bogus request.
    if _get_engine().get_session(game_id) is None:
        raise HTTPException(404, f"Game '{game_id}' not found")

    user_ip = _get_client_ip(request)
    if not _chat_limiter.check_and_record(user_ip):
        raise HTTPException(
            429,
            "Coach rate limit reached. Try again later, or run locally for unlimited "
            "coaching — see GitHub for setup instructions.",
        )
    return StreamingResponse(
        _sse_stream(coach.chat(game_id, req.message, user_id=user_ip)),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
