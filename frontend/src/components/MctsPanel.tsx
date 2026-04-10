import type { EvalResult } from '../lib/api';

interface Props {
  evaluation: EvalResult | null;
  thinking: boolean;
}

function formatQ(q: number): string {
  const sign = q >= 0 ? '+' : '';
  return `${sign}${(q * 100).toFixed(0)}%`;
}

function qColor(q: number): string {
  // Q from player's perspective: positive = good for player, negative = bad
  if (q > 0.1) return 'text-green-400';
  if (q < -0.1) return 'text-red-400';
  return 'text-text-secondary';
}

function barColor(q: number): string {
  if (q > 0.1) return 'bg-green-500';
  if (q < -0.1) return 'bg-red-500';
  return 'bg-text-secondary';
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
          <div className="text-xs text-text-secondary mb-3">
            {evaluation.total_simulations} simulations
          </div>

          <div className="flex items-center gap-3 mb-1">
            <span className="w-8" />
            <span className="flex-1" />
            <span className="text-xs font-mono text-text-secondary w-12 text-right">Eval</span>
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

                    <div className="flex-1 h-5 bg-board-slot rounded-full overflow-hidden relative">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${barColor(stat.q_value)}`}
                        style={{ width: `${Math.max(pct, 2)}%` }}
                      />
                      <span className="absolute inset-0 flex items-center justify-center text-xs font-mono text-white/90">
                        {pct}%
                      </span>
                    </div>

                    <span className={`text-xs font-mono w-12 text-right ${qColor(stat.q_value)}`}>
                      {formatQ(stat.q_value)}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="mt-3 pt-3 border-t border-border flex justify-between text-xs text-text-secondary">
            <span>Best: <span className="text-accent font-mono">Column {evaluation.best_action}</span></span>
            {(() => {
              const winPct = Math.round(50 + evaluation.root_value * 50);
              const color = winPct > 50 ? 'text-green-400' : winPct < 50 ? 'text-red-400' : 'text-text-secondary';
              return <span>Current Position: <span className={`font-mono ${color}`}>{winPct}% win</span></span>;
            })()}
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
