"""Pydantic request/response models for the game API."""

from pydantic import BaseModel, Field


# --- Requests ---

class MoveRequest(BaseModel):
    column: int = Field(ge=0, le=6, description="Column index (0-6)")


class UndoRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=42, description="Number of moves to undo")


# --- Responses ---

class MoveStatsResponse(BaseModel):
    column: int
    visits: int
    q_value: float
    prior: float
    visit_share: float


class EvalResponse(BaseModel):
    best_action: int
    root_value: float
    total_simulations: int
    move_stats: list[MoveStatsResponse]


class GameStateResponse(BaseModel):
    game_id: str
    board: list[list[int]]
    player: int = Field(description="-1 (first/X) or +1 (second/O)")
    is_terminal: bool
    winner: int | None = Field(description="-1, +1, or None (draw / in progress)")
    legal_actions: list[int]
    move_history: list[int]
    move_number: int


class AiMoveResponse(BaseModel):
    game_state: GameStateResponse
    evaluation: EvalResponse
