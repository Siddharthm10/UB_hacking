import { describe, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from '@/components/layout/Sidebar';
import { useCallStore } from '@/state/useCallStore';

vi.mock('@/lib/api', () => ({
  fetchAgentCalls: vi.fn(() =>
    Promise.resolve({
      items: [
        {
          callId: 'call-123',
          header: 'Payment arrangement follow up',
          startedAt: new Date().toISOString(),
          durationSec: 420,
          sentiment: 'positive',
          riskFlags: []
        }
      ]
    })
  )
}));

const queryClient = new QueryClient();

function renderSidebar() {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <Sidebar mobileVisible={false} setMobileVisible={() => {}} />
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('Sidebar', () => {
  it('loads calls when agent id entered', async () => {
    useCallStore.setState({ agentId: 'agent-test', selectedCallId: null });
    renderSidebar();
    const input = screen.getByPlaceholderText(/Enter agent ID/i);
    fireEvent.change(input, { target: { value: 'agent-1001' } });

    await waitFor(() => {
      expect(screen.getByText(/Payment arrangement/i)).toBeInTheDocument();
    });
  });
});
