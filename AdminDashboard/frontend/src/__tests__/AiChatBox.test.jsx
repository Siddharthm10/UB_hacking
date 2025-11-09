import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { AiChatBox } from '@/components/chat/AiChatBox';
import { useCallStore } from '@/state/useCallStore';

const listeners = {};

const socketMock = {
  connected: true,
  emit: vi.fn((event, payload) => {
    if (event === 'ai_question') {
      setTimeout(() => {
        listeners['ai_token']?.({ token: 'This ' });
        listeners['ai_token']?.({ token: 'is fine.' });
        listeners['ai_done']?.({ callId: payload.callId });
      }, 0);
    }
  }),
  on: vi.fn((event, cb) => {
    listeners[event] = cb;
  }),
  off: vi.fn((event) => {
    delete listeners[event];
  })
};

vi.mock('@/lib/socket', () => ({
  getAiSocket: () => socketMock
}));

vi.mock('@/lib/api', () => ({
  fetchAgentCalls: vi.fn(),
  fetchCallDetails: vi.fn(),
  streamAiAnswer: vi.fn()
}));

describe('AiChatBox', () => {
  it('streams assistant tokens', async () => {
    useCallStore.setState((state) => ({
      ...state,
      selectedCallId: 'call-1',
      aiChats: { 'call-1': [] },
      prompts: ['Summarize this call']
    }));
    render(<AiChatBox />);

    fireEvent.click(screen.getByRole('button', { name: /ai helper/i }));
    const textarea = screen.getByPlaceholderText(/ask anything/i);
    fireEvent.change(textarea, { target: { value: 'Summarize this call' } });
    fireEvent.submit(textarea.closest('form'));

    await waitFor(() => {
      expect(screen.getByText(/This is fine./i)).toBeInTheDocument();
    });
  });
});
