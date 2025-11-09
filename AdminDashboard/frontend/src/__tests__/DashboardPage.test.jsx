import { describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { DashboardPage } from '@/pages/DashboardPage';
import { useCallStore } from '@/state/useCallStore';

vi.mock('@/lib/api', () => ({
  fetchCallDetails: vi.fn(() =>
    Promise.resolve({
      call: {
        callId: 'call-1',
        agentId: 'agent-1',
        header: 'Escalated FDCPA concern',
        sentiment: 'neutral',
        startedAt: new Date().toISOString(),
        durationSec: 480,
        riskFlags: []
      },
      messages: [
        { callId: 'call-1', role: 'agent', text: 'Opening script', ts: new Date().toISOString(), turn: 0 }
      ]
    })
  ),
  fetchAgentCalls: vi.fn(() =>
    Promise.resolve({
      items: [
        {
          callId: 'call-1',
          header: 'Escalated FDCPA concern',
          startedAt: new Date().toISOString()
        }
      ]
    })
  )
}));

describe('DashboardPage', () => {
  it('renders call header when call data loads', async () => {
    const queryClient = new QueryClient();
    useCallStore.setState({ agentId: 'agent-1', selectedCallId: 'call-1' });
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <DashboardPage agentId="agent-1" callIdFromRoute="call-1" />
        </MemoryRouter>
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Escalated FDCPA concern/i)).toBeInTheDocument();
    });
  });
});
