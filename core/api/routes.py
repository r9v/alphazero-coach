"""Game API routes."""

import os
import time
import uuid

from fastapi import APIRouter, HTTPException, Request

MAX_GAMES_PER_DAY = int(os.environ.get("MAX_GAMES", "0"))  # 0 = unlimited
_usage: dict[str, list[float]] = {}  # ip -> list of timestamps

from core.api.models import (
    AiMoveResponse,
    EvalResponse,
    GameStateResponse,
    MoveRequest,
    MoveStatsResponse,
    UndoRequest,
)
from core.engine import Engine, GameSession, EvalResult

router = APIRouter(prefix="/game", tags=["game"])

# Engine is injected at startup via set_engine()
_engine: Engine | None = None


def set_engine(engine: Engine) -> None:
    global _engine
    _engine = engine


def _get_engine() -> Engine:
    if _engine is None:
        raise HTTPException(503, "Engine not initialized")
    return _engine


def _session_to_response(game_id: str, session: GameSession) -> GameStateResponse:
    return GameStateResponse(
        game_id=game_id,
        board=session.board,
        player=session.player,
        is_terminal=session.is_terminal,
        winner=session.winner,
        legal_actions=session.legal_actions,
        move_history=session.move_history,
        move_number=session.move_number,
    )


def _eval_to_response(result: EvalResult) -> EvalResponse:
    return EvalResponse(
        best_action=result.best_action,
        root_value=result.root_value,
        total_simulations=result.total_simulations,
        move_stats=[
            MoveStatsResponse(
                column=m.column,
                visits=m.visits,
                q_value=m.q_value,
                prior=m.prior,
                visit_share=m.visit_share,
            )
            for m in result.move_stats
        ],
    )


def _get_session(game_id: str) -> GameSession:
    session = _get_engine().get_session(game_id)
    if session is None:
        raise HTTPException(404, f"Game '{game_id}' not found")
    return session


@router.post("/new", response_model=GameStateResponse)
def new_game(request: Request):
    if MAX_GAMES_PER_DAY:
        ip = request.client.host if request.client else "unknown"
        now = time.time()
        day_ago = now - 86400
        # Prune old entries and count recent games
        _usage[ip] = [t for t in _usage.get(ip, []) if t > day_ago]
        if len(_usage[ip]) >= MAX_GAMES_PER_DAY:
            raise HTTPException(
                429,
                f"Demo limit reached ({MAX_GAMES_PER_DAY} games/day). Run locally for unlimited play — see GitHub for setup instructions.",
            )
        _usage[ip].append(now)
    game_id = uuid.uuid4().hex[:8]
    session = _get_engine().new_game(game_id)
    return _session_to_response(game_id, session)


@router.post("/{game_id}/move", response_model=GameStateResponse)
def player_move(game_id: str, req: MoveRequest):
    _get_session(game_id)  # validate exists
    try:
        session = _get_engine().player_move(game_id, req.column)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return _session_to_response(game_id, session)


@router.post("/{game_id}/ai-move", response_model=AiMoveResponse)
def ai_move(game_id: str):
    _get_session(game_id)
    try:
        session, eval_result = _get_engine().ai_move(game_id)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return AiMoveResponse(
        game_state=_session_to_response(game_id, session),
        evaluation=_eval_to_response(eval_result),
    )


@router.post("/{game_id}/evaluate", response_model=EvalResponse)
def evaluate(game_id: str):
    _get_session(game_id)
    result = _get_engine().evaluate_position(game_id)
    return _eval_to_response(result)


@router.post("/{game_id}/undo", response_model=GameStateResponse)
def undo(game_id: str, req: UndoRequest | None = None):
    _get_session(game_id)
    count = req.count if req else 1
    session = _get_engine().undo(game_id, count)
    return _session_to_response(game_id, session)


