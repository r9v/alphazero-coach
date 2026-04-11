import { useCallback, useEffect, useRef, useState } from 'react';
import Markdown from 'react-markdown';
import { useCoachChat } from '../hooks/useCoachChat';
import LoadingDots from './LoadingDots';

interface Props {
  gameId: string | null;
  moveNumber: number;
  isTerminal: boolean;
}

const MESSAGE_STYLES = {
  user: 'bg-accent/10 border border-accent/20 rounded-lg px-3 py-2 text-accent',
  error: 'bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 text-red-400',
  coach: 'text-text-primary leading-relaxed',
} as const;

export default function CoachPanel({ gameId, moveNumber, isTerminal }: Props) {
  const { messages, streaming, sendQuestion } = useCoachChat(gameId, moveNumber, isTerminal);
  const [question, setQuestion] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleAsk = useCallback(() => {
    if (!question.trim()) return;
    const q = question.trim();
    setQuestion('');
    sendQuestion(q);
  }, [question, sendQuestion]);

  return (
    <div className="bg-surface-alt rounded-xl border border-border flex flex-col h-96">
      <div className="px-4 py-3 border-b border-border flex items-center gap-2">
        <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wide">
          AI Coach
        </h3>
        {streaming && <LoadingDots color="bg-green-400" />}
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <p className="text-sm text-text-secondary">
            Play a move to get coaching analysis. You can also ask questions below.
          </p>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`text-sm ${MESSAGE_STYLES[msg.role]}`}>
              {msg.content ? (
                msg.role === 'coach' ? <Markdown>{msg.content}</Markdown> : msg.content
              ) : (streaming && i === messages.length - 1 ? (
                <span className="text-text-secondary">Thinking...</span>
              ) : null)}
            </div>
          ))
        )}
      </div>

      <div className="p-3 border-t border-border">
        <form
          onSubmit={(e) => { e.preventDefault(); handleAsk(); }}
          className="flex gap-2"
        >
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask the coach..."
            disabled={streaming || !gameId}
            className="flex-1 min-w-0 bg-board-slot border border-border rounded-lg px-3 py-2 text-sm text-text-primary placeholder-text-secondary focus:outline-none focus:border-accent disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={streaming || !question.trim() || !gameId}
            className="px-3 py-2 bg-accent text-white text-sm rounded-lg hover:bg-accent/80 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          >
            Ask
          </button>
        </form>
      </div>
    </div>
  );
}
