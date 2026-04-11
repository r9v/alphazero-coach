"""Game engine wrapper around alphazero-boardgames.

Loads the trained Connect 4 model, manages game state, and exposes
MCTS evaluation for the coaching agent and API layer.
"""

import sys
import os
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# Add the alphazero-boardgames repo to sys.path so we can import it directly.
# In production this would be pip-installed, but for development we reference
# the sibling directory.
_AZ_DIR = os.environ.get(
    "ALPHAZERO_DIR",
    str(Path(__file__).resolve().parent.parent.parent / "connect4-alphazero"),
)
if _AZ_DIR not in sys.path:
    sys.path.insert(0, _AZ_DIR)

from game_configs import GAME_CONFIGS
from mcts import MCTS
from utils import load_game, make_net


GAME_NAME = "connect4"


@dataclass
class MoveStats:
    """MCTS statistics for a single candidate move."""
    column: int
    visits: int
    q_value: float          # mean value from MCTS (-1 to +1, from AI's perspective)
    prior: float            # network policy prior
    visit_share: float      # fraction of total visits


@dataclass
class EvalResult:
    """Full MCTS evaluation result for a position."""
    best_action: int
    root_value: float       # network value estimate at root
    total_simulations: int
    move_stats: list[MoveStats]


@dataclass
class GameSession:
    """A single game session tracking state history for undo support."""
    states: list            # list of GameState objects
    move_history: list[int] = field(default_factory=list)

    @property
    def current_state(self):
        return self.states[-1]

    @property
    def board(self) -> list[list[int]]:
        return self.current_state.board.tolist()

    @property
    def player(self) -> int:
        return int(self.current_state.player)

    @property
    def is_terminal(self) -> bool:
        return bool(self.current_state.terminal)

    @property
    def winner(self) -> int | None:
        if not self.is_terminal:
            return None
        v = int(self.current_state.terminal_value)
        return v if v != 0 else None  # None = draw

    @property
    def legal_actions(self) -> list[int]:
        return [int(a) for a in np.nonzero(self.current_state.available_actions)[0]]

    @property
    def move_number(self) -> int:
        return len(self.move_history)


class Engine:
    """Connect 4 engine backed by AlphaZero MCTS."""

    def __init__(self, checkpoint_dir: str | None = None, simulations: int = 400, ai_simulations: int = 200):
        self.game = load_game(GAME_NAME)
        cfg = GAME_CONFIGS[GAME_NAME]

        self.net = make_net(self.game, GAME_NAME)
        self.simulations = simulations        # for evaluation/coaching tools
        self.ai_simulations = ai_simulations  # for AI opponent (weaker)

        # Load trained weights
        ckpt_dir = checkpoint_dir or os.path.join(_AZ_DIR, "checkpoints", GAME_NAME)
        loaded = self.net.load_latest(ckpt_dir)
        if loaded:
            print(f"[engine] Loaded checkpoint: {loaded}")
        else:
            print("[engine] WARNING: No checkpoint found, using untrained network")

        self.net.eval()

        self.mcts = MCTS(self.game, self.net, c_puct=cfg.get("play_c_puct", 2.5))
        self._sessions: dict[str, GameSession] = {}

    def new_game(self, game_id: str) -> GameSession:
        state = self.game.new_game()
        session = GameSession(states=[state])
        self._sessions[game_id] = session
        return session

    def get_session(self, game_id: str) -> GameSession | None:
        return self._sessions.get(game_id)

    def player_move(self, game_id: str, column: int) -> GameSession:
        session = self._sessions[game_id]
        if session.is_terminal:
            raise ValueError("Game is already over")
        if column not in session.legal_actions:
            raise ValueError(f"Column {column} is not a legal move")

        new_state = self.game.step(session.current_state, column)
        session.states.append(new_state)
        session.move_history.append(column)
        return session

    def ai_move(self, game_id: str) -> GameSession:
        session = self._sessions[game_id]
        if session.is_terminal:
            raise ValueError("Game is already over")

        result = self.evaluate(session, simulations=self.ai_simulations)

        # Temperature schedule for move variety
        if session.move_number < 6:
            temp = 0.8
        elif session.move_number < 11:
            temp = 0.5
        else:
            temp = 0.2

        visits = np.array([m.visit_share for m in result.move_stats])
        cols = np.array([m.column for m in result.move_stats])
        probs = visits ** (1 / temp)
        probs = probs / probs.sum()
        action = int(np.random.choice(cols, p=probs))

        new_state = self.game.step(session.current_state, action)
        session.states.append(new_state)
        session.move_history.append(action)
        return session

    def evaluate(self, session: GameSession, simulations: int | None = None) -> EvalResult:
        """Run MCTS on the current position and return detailed stats."""
        state = session.current_state
        pi = self.mcts.get_policy(simulations or self.simulations, state)
        root = self.mcts.last_root

        best_action = int(np.argmax(pi))
        total_sims = int(root.n)

        move_stats = []
        for a in range(self.game.action_size):
            child = root.children[a]
            if child and child.n > 0:
                move_stats.append(MoveStats(
                    column=a,
                    visits=int(child.n),
                    q_value=float(child.Q),
                    prior=float(root.P[a]),
                    visit_share=float(pi[a]),
                ))

        move_stats.sort(key=lambda m: m.visits, reverse=True)

        # Use the search-corrected Q-value of the best move, not the raw nnet_value.
        # nnet_value is the neural network's initial guess; Q is refined by MCTS search
        # and is far more accurate (especially in endgame positions).
        best_child = root.children[best_action]
        root_q = float(best_child.Q) if best_child and best_child.n > 0 else float(root.nnet_value)

        return EvalResult(
            best_action=best_action,
            root_value=root_q,
            total_simulations=total_sims,
            move_stats=move_stats,
        )

    def evaluate_position(self, game_id: str) -> EvalResult:
        """Evaluate the current position for a game session."""
        session = self._sessions[game_id]
        return self.evaluate(session)
