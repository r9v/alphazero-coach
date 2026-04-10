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

  const displayRows = [...Array(ROWS)].map((_, i) => ROWS - 1 - i);
  const isLegal = (col: number) => legalActions.includes(col);

  const landingRow = (col: number): number | null => {
    for (let r = 0; r < ROWS; r++) {
      if (board[r][col] === 0) return r;
    }
    return null;
  };

  const cell = 'aspect-square w-full';
  const piece = 'aspect-square w-[85%]';

  return (
    <div className="w-full lg:w-[450px] lg:shrink-0 xl:w-[560px]">
      {/* Board frame */}
      <div className="bg-board-blue rounded-xl p-1.5 sm:p-2.5 shadow-2xl">
        <div className="grid grid-cols-7 gap-1 sm:gap-2">
          {displayRows.map((row) =>
            [...Array(COLS)].map((_, col) => {
              const val = board[row][col];
              const isLastMove = lastMove === col && val !== 0 &&
                (row === ROWS - 1 || board[row + 1][col] === 0);
              const isHoverTarget = hoverCol === col && val === 0 &&
                landingRow(col) === row && isLegal(col) && !disabled;

              return (
                <div
                  key={`${row}-${col}`}
                  className={`${cell} rounded-full bg-board-slot flex items-center justify-center cursor-pointer transition-colors hover:bg-board-slot/80`}
                  onMouseEnter={() => setHoverCol(col)}
                  onMouseLeave={() => setHoverCol(null)}
                  onClick={() => {
                    if (!disabled && isLegal(col)) onMove(col);
                  }}
                >
                  {val !== 0 ? (
                    <div
                      className={`${piece} rounded-full ${pieceColor(val)} ${pieceShadow(val)} ${
                        isLastMove ? 'animate-drop' : ''
                      }`}
                    />
                  ) : isHoverTarget ? (
                    <div className={`${piece} rounded-full bg-piece-red/20 border-2 border-piece-red/30`} />
                  ) : null}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Column numbers */}
      <div className="grid grid-cols-7 gap-1 sm:gap-2 mt-2 px-2">
        {[...Array(COLS)].map((_, col) => (
          <div key={col} className="text-center text-xs text-text-secondary font-mono">
            {col}
          </div>
        ))}
      </div>
    </div>
  );
}
