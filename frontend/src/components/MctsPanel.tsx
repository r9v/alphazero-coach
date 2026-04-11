import type { EvalResult } from '../lib/api';

interface Props {
  evaluation: EvalResult | null;
  thinking: boolean;
}

export default function MctsPanel({ evaluation, thinking }: Props) {
  return (
    <div className="bg-surface-alt rounded-xl border border-border p-4">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wide">
          Your Next Recommended Move
        </h3>
        {thinking && (
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
            <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse [animation-delay:150ms]" />
            <div className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse [animation-delay:300ms]" />
          </div>
        )}
      </div>

      {evaluation ? (
        <>
          <div className="mb-3 flex justify-between text-xs text-text-secondary">
            <span>Best: <span className="text-accent font-mono">Column {evaluation.best_action}</span></span>
            {(() => {
              const winPct = Math.round(50 + evaluation.root_value * 50);
              const color = winPct > 50 ? 'text-green-400' : winPct < 50 ? 'text-red-400' : 'text-text-secondary';
              return <span>Current Position: <span className={`font-mono ${color}`}>{winPct}% win</span></span>;
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
