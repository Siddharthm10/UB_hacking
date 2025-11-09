import axios from 'axios';

const apiBase = typeof __API_BASE__ !== 'undefined' ? __API_BASE__ : 'http://localhost:8000';

export const api = axios.create({
  baseURL: `${apiBase}/api`,
  headers: {
    'Content-Type': 'application/json'
  }
});

export function fetchAgentCalls({ agentId, cursor, limit = 20 }) {
  if (!agentId) return Promise.resolve({ items: [] });
  return api
    .get(`/agents/${agentId}/calls`, {
      params: { cursor, limit }
    })
    .then((res) => res.data);
}

export function fetchCallDetails(callId) {
  if (!callId) return Promise.resolve(null);
  return api.get(`/calls/${callId}`).then((res) => res.data);
}

export function fetchCallMessages({ callId, cursor, limit = 200 }) {
  if (!callId) return Promise.resolve({ items: [] });
  return api
    .get(`/calls/${callId}/messages`, {
      params: { cursor, limit }
    })
    .then((res) => res.data);
}

export function streamAiAnswer({ callId, question, onToken, onDone, onError }) {
  const controller = new AbortController();
  const decoder = new TextDecoder('utf-8');

  fetch(`${apiBase}/api/ai/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ callId, question }),
    signal: controller.signal
  })
    .then(async (res) => {
      const reader = res.body.getReader();
      let buffer = '';
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split('\n\n');
        parts.forEach((part, idx) => {
          const line = part.trim();
          if (!line) return;
          if (idx === parts.length - 1 && !buffer.endsWith('\n\n')) {
            buffer = part;
            return;
          }
          if (line.startsWith('data:')) {
            try {
              const payload = JSON.parse(line.replace('data:', '').trim());
              if (payload.token && onToken) onToken(payload.token);
              if (payload.done && onDone) onDone(payload);
            } catch (error) {
              if (onError) onError(error);
            }
          }
        });
        if (buffer.endsWith('\n\n')) buffer = '';
      }
      if (onDone) onDone({ done: true });
    })
    .catch((err) => {
      if (onError) onError(err);
    });

  return () => controller.abort();
}
