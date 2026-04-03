interface Props {
  player: number;
  moveNumber: number;
  isTerminal: boolean;
  winner: number | null;
  thinking: boolean;
}

export default function GameInfo({ player, moveNumber, isTerminal, winner, thinking }: Props) {
  let status: string;
  let statusColor = 'text-text-secondary';

  if (isTerminal) {
    if (winner === -1) {
      status = 'Red wins!';
      statusColor = 'text-piece-red';
    } else if (winner === 1) {
      status = 'Yellow wins!';
      statusColor = 'text-piece-yellow';
    } else {
      status = 'Draw!';
      statusColor = 'text-text-secondary';
    }
  } else if (thinking) {
    status = 'AI is thinking...';
    statusColor = 'text-accent';
  } else {
    const turn = player === -1 ? 'Red' : 'Yellow';
    const turnColor = player === -1 ? 'text-piece-red' : 'text-piece-yellow';
    return (
      <div className="flex items-center gap-4 text-sm">
        <span className="text-text-secondary">Move {moveNumber + 1}</span>
        <span className="text-text-secondary">|</span>
        <span className={turnColor}>
          <span className={`inline-block w-3 h-3 rounded-full mr-1.5 ${
            player === -1 ? 'bg-piece-red' : 'bg-piece-yellow'
          }`} />
          {turn}'s turn
        </span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-4 text-sm">
      <span className="text-text-secondary">Move {moveNumber}</span>
      <span className="text-text-secondary">|</span>
      <span className={statusColor}>{status}</span>
    </div>
  );
}
