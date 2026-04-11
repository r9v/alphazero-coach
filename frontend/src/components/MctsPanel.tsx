import type { EvalResult } from '../lib/api';
import LoadingDots from './LoadingDots';

interface Props {
  evaluation: EvalResult | null;
  thinking: boolean;
  isTerminal: boolean;
  winner: number | null;
}

export default function MctsPanel({ evaluation, thinking, isTerminal, winner }: Props) {
  if (isTerminal) {
    const result = winner === -1 ? 'Red wins!' : winner === 1 ? 'Yellow wins!' : 'Draw!';
    const color = winner === -1 ? 'text-piece-red' : winner === 1 ? 'text-piece-yellow' : 'text-text-secondary';
    return (
      <div className="bg-surface-alt rounded-xl border border-border p-4">
        <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wide mb-3">
          Game Over
        </h3>
        <p className={`text-lg font-bold ${color}`}>{result}</p>
      </div>
    );
  }

  return (
    <div className="bg-surface-alt rounded-xl border border-border p-4">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wide">
          Your Next Recommended Move
        </h3>
        {thinking && <LoadingDots />}
      </div>

      {evaluation ? (
        <>
          <div className="mb-3 flex justify-between text-xs text-text-secondary">
            <span>Best: <span className="text-accent font-mono">Column {evaluation.best_action}</span></span>
            {(() => {
              const winPct = 50 + evaluation.root_value * 50;
              let label: string;
              let color: string;
              if (winPct >= 80)      { label = 'Strongly winning'; color = 'text-green-400'; }
              else if (winPct >= 60) { label = 'Slightly winning'; color = 'text-green-400'; }
              else if (winPct >= 40) { label = 'Draw';             color = 'text-text-secondary'; }
              else if (winPct >= 20) { label = 'Slightly losing';  color = 'text-red-400'; }
              else                   { label = 'Strongly losing';  color = 'text-red-400'; }
              return <span>Outlook: <span className={`font-mono ${color}`}>{label}</span></span>;
            })()}
          </div>

          <div className="space-y-2">
            {evaluation.move_stats.map((stat) => {
              const pct = Math.round(stat.visit_share * 100);
              const isBest = stat.column === evaluation.best_action;

              return (
                <div key={stat.column} className="group">
                  <div className="flex items-center gap-3">
                    <span className={`text-sm font-mono w-8 ${
                      isBest ? 'text-accent font-bold' : 'text-text-secondary'
                    }`}>
                      C{stat.column}
                    </span>

                    <div className="flex-1 h-5 bg-board-slot rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500 bg-text-secondary"
                        style={{ width: `${Math.max(pct, 2)}%` }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

        </>
      ) : (
        <p className="text-sm text-text-secondary">
          {thinking ? 'AI is thinking...' : 'Make a move to see analysis'}
        </p>
      )}
    </div>
  );
}
