import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../lib/api';

interface Message {
  role: 'coach' | 'user' | 'error';
  content: string;
}

interface Props {
  gameId: string | null;
  moveNumber: number;
  isTerminal: boolean;
}

export default function CoachPanel({ gameId, moveNumber, isTerminal }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [question, setQuestion] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastAnalyzedMove = useRef(0);

  const scrollToBottom = () => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  };

  const appendToken = (token: string) => {
    setMessages((prev) => {
      const updated = [...prev];
      const last = updated[updated.length - 1];
      if (last && last.role === 'coach') {
        updated[updated.length - 1] = { ...last, content: last.content + token };
      }
      return updated;
    });
    scrollToBottom();
  };

  const handleStreamError = (err: unknown) => {
    setStreaming(false);
    const raw = err instanceof Error ? err.message : 'Coach unavailable';
    const msg = raw.includes('429') || raw.includes('RESOURCE_EXHAUSTED') || raw.includes('quota') || raw.includes('rate')
      ? 'LLM API rate limit reached. Try again later or check your API plan.'
      : raw;
    // Replace empty "Thinking..." message with error
    setMessages((prev) => {
      const updated = [...prev];
      const last = updated[updated.length - 1];
      if (last && last.role === 'coach' && !last.content) {
        updated[updated.length - 1] = { role: 'error', content: msg };
      } else {
        updated.push({ role: 'error', content: msg });
      }
      return updated;
    });
  };

  const startStream = (streamFn: () => Promise<void>) => {
    setStreaming(true);
    setMessages((prev) => [...prev, { role: 'coach', content: '' }]);
    streamFn().catch(handleStreamError);
  };

  // Auto-analyze after each AI move
  useEffect(() => {
    if (!gameId || moveNumber < 2) return;
    if (moveNumber <= lastAnalyzedMove.current) return;

    lastAnalyzedMove.current = moveNumber;
    startStream(() =>
      api.streamCoachAnalysis(gameId, appendToken, () => setStreaming(false))
    );
  }, [gameId, moveNumber]);

  // Trigger on game over
  useEffect(() => {
    if (!gameId || !isTerminal) return;
    if (lastAnalyzedMove.current === -1) return;
    lastAnalyzedMove.current = -1;

    startStream(() =>
      api.streamCoachAnalysis(gameId, appendToken, () => setStreaming(false))
    );
  }, [gameId, isTerminal]);

  // Reset on new game
  useEffect(() => {
    setMessages([]);
    lastAnalyzedMove.current = 0;
  }, [gameId]);

  const handleAsk = useCallback(() => {
    if (!gameId || !question.trim() || streaming) return;

    const q = question.trim();
    setQuestion('');
    setMessages((prev) => [...prev, { role: 'user', content: q }]);

    startStream(() =>
      api.streamCoachAsk(gameId, q, appendToken, () => setStreaming(false))
    );
  }, [gameId, question, streaming]);

  return (
    <div className="bg-surface-alt rounded-xl border border-border flex flex-col h-96">
      <div className="px-4 py-3 border-b border-border flex items-center gap-2">
        <h3 className="text-sm font-semibold text-text-primary uppercase tracking-wide">
          AI Coach
        </h3>
        {streaming && (
          <div className="flex gap-1">
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse [animation-delay:150ms]" />
            <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse [animation-delay:300ms]" />
          </div>
        )}
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <p className="text-sm text-text-secondary">
            Play a move to get coaching analysis. You can also ask questions below.
          </p>
        ) : (
          messages.map((msg, i) => (
            <div
              key={i}
              className={`text-sm ${
                msg.role === 'user'
                  ? 'bg-accent/10 border border-accent/20 rounded-lg px-3 py-2 text-accent'
                  : msg.role === 'error'
                  ? 'bg-red-500/10 border border-red-500/20 rounded-lg px-3 py-2 text-red-400'
                  : 'text-text-primary leading-relaxed'
              }`}
            >
              {msg.content || (streaming && i === messages.length - 1 ? (
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
