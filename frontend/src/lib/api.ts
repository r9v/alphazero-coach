const BASE = '';

export interface MoveStats {
  column: number;
  visits: number;
  q_value: number;
  prior: number;
  visit_share: number;
}

export interface EvalResult {
  best_action: number;
  root_value: number;
  total_simulations: number;
  move_stats: MoveStats[];
}

export interface GameState {
  game_id: string;
  board: number[][];
  player: number;
  is_terminal: boolean;
  winner: number | null;
  legal_actions: number[];
  move_history: number[];
  move_number: number;
}

export interface AiMoveResponse {
  game_state: GameState;
  evaluation: EvalResult;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res.json();
}

export const api = {
  newGame: () => request<GameState>('/game/new', { method: 'POST' }),

  playerMove: (id: string, column: number) =>
    request<GameState>(`/game/${id}/move`, {
      method: 'POST',
      body: JSON.stringify({ column }),
    }),

  aiMove: (id: string) =>
    request<AiMoveResponse>(`/game/${id}/ai-move`, { method: 'POST' }),

  undo: (id: string, count = 1) =>
    request<GameState>(`/game/${id}/undo`, {
      method: 'POST',
      body: JSON.stringify({ count }),
    }),

  streamCoachAnalysis: (id: string, onToken: (text: string) => void, onDone: () => void) =>
    streamSSE(`/coach/${id}/analyze`, {}, onToken, onDone),

  streamCoachAsk: (id: string, question: string, onToken: (text: string) => void, onDone: () => void) =>
    streamSSE(`/coach/${id}/ask`, { question }, onToken, onDone),
};

async function streamSSE(
  path: string,
  body: Record<string, unknown>,
  onToken: (text: string) => void,
  onDone: () => void,
) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (!line.startsWith('data: ')) continue;
      let event;
      try {
        event = JSON.parse(line.slice(6));
      } catch {
        continue; // skip malformed JSON
      }
      if (event.type === 'token') {
        // Gemini sometimes sends content as [{type:"text", text:"..."}] instead of a string
        const content = event.content;
        if (typeof content === 'string') {
          onToken(content);
        } else if (Array.isArray(content)) {
          const text = content.map((c: { text?: string }) => c.text || '').join('');
          if (text) onToken(text);
        }
      } else if (event.type === 'done') {
        onDone();
        return;
      } else if (event.type === 'error') {
        throw new Error(event.content);
      }
    }
  }
  onDone();
}
