import { useCallback, useEffect, useRef, useState } from 'react';
import { api, classifyApiError } from '../lib/api';

export interface Message {
  role: 'coach' | 'user' | 'error';
  content: string;
}

const AUTO_MSG = 'A new move was played. Grade my last move, check the board, and recommend my next move. If a strategy concept applies, look it up.';
const GAME_OVER_MSG = 'The game is over. Analyze the full game and tell me about the turning point.';

export function useCoachChat(gameId: string | null, moveNumber: number, isTerminal: boolean) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const lastAnalyzedMove = useRef(0);
  const streamingRef = useRef(false);
  const pendingMove = useRef<number | null>(null);

  const appendToken = useCallback((token: string) => {
    setMessages((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.role === 'coach') {
        const updated = [...prev];
        updated[updated.length - 1] = { ...last, content: last.content + token };
        return updated;
      }
      return prev;
    });
  }, []);

  const handleStreamError = useCallback((err: unknown) => {
    streamingRef.current = false;
    setStreaming(false);
    const msg = classifyApiError(err);
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
  }, []);

  const doSend = useCallback((gid: string, message: string) => {
    streamingRef.current = true;
    setStreaming(true);
    setMessages((prev) => [...prev, { role: 'coach', content: '' }]);
    api.streamCoachChat(gid, message, appendToken, () => {
      streamingRef.current = false;
      setStreaming(false);
      if (pendingMove.current !== null) {
        lastAnalyzedMove.current = pendingMove.current;
        pendingMove.current = null;
      }
    }).catch(handleStreamError);
  }, [appendToken, handleStreamError]);

  // Auto-analyze after each AI move (skip if game just ended — let game-over effect handle it)
  useEffect(() => {
    if (!gameId || moveNumber < 2 || isTerminal) return;
    if (moveNumber % 2 !== 0) return;
    if (moveNumber <= lastAnalyzedMove.current) return;

    if (streamingRef.current) {
      pendingMove.current = moveNumber;
      return;
    }
    lastAnalyzedMove.current = moveNumber;
    doSend(gameId, AUTO_MSG);
  }, [gameId, moveNumber, isTerminal, doSend]);

  // Trigger on game over
  useEffect(() => {
    if (!gameId || !isTerminal) return;
    if (lastAnalyzedMove.current === -1) return;
    lastAnalyzedMove.current = -1;

    if (streamingRef.current) return;
    doSend(gameId, GAME_OVER_MSG);
  }, [gameId, isTerminal, doSend]);

  // Reset on new game
  useEffect(() => {
    setMessages([]);
    lastAnalyzedMove.current = 0;
    pendingMove.current = null;
  }, [gameId]);

  const sendQuestion = useCallback((question: string) => {
    if (!gameId || !question.trim() || streamingRef.current) return;
    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    doSend(gameId, question);
  }, [gameId, doSend]);

  return { messages, streaming, sendQuestion };
}
