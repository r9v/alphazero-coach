import { useCallback, useEffect, useState } from 'react';
import { api, type GameState, type EvalResult } from './lib/api';
import Board from './components/Board';
import Card from './components/Card';
import MctsPanel from './components/MctsPanel';
import GameInfo from './components/GameInfo';
import CoachPanel from './components/CoachPanel';

const HUMAN_PLAYER = -1; // Human plays first (red)

export default function App() {
  const [game, setGame] = useState<GameState | null>(null);
  const [evaluation, setEvaluation] = useState<EvalResult | null>(null);
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startNewGame = useCallback(async () => {
    try {
      setError(null);
      setEvaluation(null);
      const state = await api.newGame();
      setGame(state);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start game');
    }
  }, []);

  useEffect(() => {
    startNewGame();
  }, [startNewGame]);

  const handleMove = useCallback(async (col: number) => {
    if (!game || thinking || game.is_terminal) return;

    try {
      setError(null);
      // Player move
      const afterPlayer = await api.playerMove(game.game_id, col);
      setGame(afterPlayer);

      if (afterPlayer.is_terminal) return;

      // AI move
      setThinking(true);
      const gameAfterAi = await api.aiMove(game.game_id);
      setGame(gameAfterAi);

      // Evaluate from player's perspective (recommended next move)
      if (!gameAfterAi.is_terminal) {
        const eval_ = await api.evaluate(game.game_id);
        setEvaluation(eval_);
      }
      setThinking(false);
    } catch (e) {
      setThinking(false);
      setError(e instanceof Error ? e.message : 'Move failed');
    }
  }, [game, thinking]);



  if (!game) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-text-secondary">
          {error ? (
            <div className="text-center">
              <p className="text-red-400 mb-4">{error}</p>
              <button
                onClick={startNewGame}
                className="px-4 py-2 bg-accent text-white rounded-lg hover:bg-accent/80 transition-colors"
              >
                Retry
              </button>
            </div>
          ) : (
            'Loading...'
          )}
        </div>
      </div>
    );
  }

  const lastMove = game.move_history.length > 0
    ? game.move_history[game.move_history.length - 1]
    : null;

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b border-border px-6 py-4">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <h1 className="text-lg font-semibold text-text-primary">AlphaZero Coach</h1>
            <span className="hidden sm:inline text-xs px-2 py-0.5 bg-accent/10 text-accent rounded-full border border-accent/20">
              Connect 4
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={startNewGame}
              disabled={thinking}
              className="px-3 py-1.5 text-sm bg-accent text-white rounded-lg hover:bg-accent/80 transition-colors disabled:opacity-50"
            >
              New Game
            </button>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="flex-1 px-3 py-4 sm:px-6 sm:py-6">
        <div className="max-w-6xl mx-auto flex flex-col items-center lg:flex-row lg:items-start gap-6">
          {/* Left: Board */}
          <div className="w-full lg:w-auto flex flex-col items-center gap-4">
            <Board
              board={game.board}
              legalActions={game.legal_actions}
              onMove={handleMove}
              disabled={thinking || game.is_terminal || game.player !== HUMAN_PLAYER}
              lastMove={lastMove}
            />
            <GameInfo
              player={game.player}
              moveNumber={game.move_number}
              isTerminal={game.is_terminal}
              winner={game.winner}
              thinking={thinking}
            />
          </div>

          {/* Right: Analysis + Coach panels */}
          <div className="w-full lg:flex-1 lg:min-w-0 flex flex-col gap-4">
            <CoachPanel
              gameId={game.game_id}
              moveNumber={game.move_number}
              isTerminal={game.is_terminal}
            />
            <MctsPanel evaluation={evaluation} thinking={thinking} />

            {/* Move history */}
            {game.move_history.length > 0 && (
              <Card title="Move History">
                <div className="flex flex-wrap gap-1">
                  {game.move_history.map((move, i) => (
                    <span
                      key={i}
                      className={`inline-flex items-center gap-1 text-xs font-mono px-2 py-1 rounded ${
                        i % 2 === 0
                          ? 'bg-piece-red/10 text-piece-red'
                          : 'bg-piece-yellow/10 text-piece-yellow'
                      }`}
                    >
                      <span className="text-text-secondary">{i + 1}.</span>
                      C{move}
                    </span>
                  ))}
                </div>
              </Card>
            )}

            {error && (
              <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-3 text-sm text-red-400">
                {error}
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}
