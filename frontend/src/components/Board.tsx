import { useState } from 'react';

const ROWS = 6;
const COLS = 7;

interface Props {
  board: number[][];
  legalActions: number[];
  onMove: (col: number) => void;
  disabled: boolean;
  lastMove: number | null;
}

function pieceColor(val: number): string {
  if (val === -1) return 'bg-piece-red';
  if (val === 1) return 'bg-piece-yellow';
  return '';
}

function pieceShadow(val: number): string {
  if (val === -1) return 'shadow-[inset_0_-4px_8px_rgba(0,0,0,0.3),0_0_12px_rgba(239,68,68,0.3)]';
  if (val === 1) return 'shadow-[inset_0_-4px_8px_rgba(0,0,0,0.3),0_0_12px_rgba(234,179,8,0.3)]';
  return '';
}

export default function Board({ board, legalActions, onMove, disabled, lastMove }: Props) {
  const [hoverCol, setHoverCol] = useState<number | null>(null);

  // Board is stored as board[row][col] with row 0 = bottom
  // We render top-to-bottom so reverse the row order
  const displayRows = [...Array(ROWS)].map((_, i) => ROWS - 1 - i);

  const isLegal = (col: number) => legalActions.includes(col);

  // Find the row where a piece would land in a column (for hover preview)
  const landingRow = (col: number): number | null => {
    for (let r = 0; r < ROWS; r++) {
      if (board[r][col] === 0) return r;
    }
    return null;
  };

  return (
    <div className="inline-block">
      {/* Column hover indicators */}
      <div className="grid grid-cols-7 gap-1 mb-1 px-2">
        {[...Array(COLS)].map((_, col) => (
          <div key={col} className="flex justify-center h-6">
            {hoverCol === col && isLegal(col) && !disabled && (
              <div className="w-3 h-3 rounded-full bg-piece-red/60 animate-pulse mt-auto" />
            )}
          </div>
        ))}
      </div>

      {/* Board frame */}
      <div className="bg-board-blue rounded-xl p-2 shadow-2xl">
        <div className="grid grid-cols-7 gap-1.5">
          {displayRows.map((row) =>
            [...Array(COLS)].map((col_unused, col) => {
              const val = board[row][col];
              const isLastMove = lastMove === col && val !== 0 &&
                // Check this is the top piece in the column
                (row === ROWS - 1 || board[row + 1][col] === 0);
              const isHoverTarget = hoverCol === col && val === 0 &&
                landingRow(col) === row && isLegal(col) && !disabled;

              return (
                <div
                  key={`${row}-${col}`}
                  className="w-14 h-14 rounded-full bg-board-slot flex items-center justify-center cursor-pointer transition-colors hover:bg-board-slot/80"
                  onMouseEnter={() => setHoverCol(col)}
                  onMouseLeave={() => setHoverCol(null)}
                  onClick={() => {
                    if (!disabled && isLegal(col)) onMove(col);
                  }}
                >
                  {val !== 0 ? (
                    <div
                      className={`w-12 h-12 rounded-full ${pieceColor(val)} ${pieceShadow(val)} ${
                        isLastMove ? 'animate-drop' : ''
                      }`}
                    />
                  ) : isHoverTarget ? (
                    <div className="w-12 h-12 rounded-full bg-piece-red/20 border-2 border-piece-red/30" />
                  ) : null}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Column numbers */}
      <div className="grid grid-cols-7 gap-1 mt-2 px-2">
        {[...Array(COLS)].map((_, col) => (
          <div key={col} className="text-center text-xs text-text-secondary font-mono">
            {col}
          </div>
        ))}
      </div>
    </div>
  );
}
