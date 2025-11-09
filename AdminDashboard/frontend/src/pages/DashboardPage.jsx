import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { fetchCallDetails } from '@/lib/api';
import { useCallStore } from '@/state/useCallStore';
import { CallDetails } from '@/components/calls/CallDetails';
import { CallInsightsPanel } from '@/components/calls/CallInsightsPanel';
import { AiChatBox } from '@/components/chat/AiChatBox';
import { Skeleton } from '@/components/common/Skeleton';
import LandingPage from '@/pages/LandingPage';

export function DashboardPage({ agentId, callIdFromRoute }) {
  const {
    selectedCallId,
    setSelectedCallId,
    agentId: storeAgent,
    setAgentId
  } = useCallStore();

  useEffect(() => {
    if (agentId && agentId !== storeAgent) {
      setAgentId(agentId);
    }
  }, [agentId, setAgentId, storeAgent]);

  useEffect(() => {
    if (callIdFromRoute && callIdFromRoute !== selectedCallId) {
      setSelectedCallId(callIdFromRoute);
    }
  }, [callIdFromRoute, selectedCallId, setSelectedCallId]);

  // no auto-selection; wait for user to pick a call

  const activeCallId = callIdFromRoute || selectedCallId;

  const { data, isLoading } = useQuery({
    queryKey: ['call', activeCallId],
    queryFn: () => fetchCallDetails(activeCallId),
    enabled: Boolean(activeCallId)
  });

  const call = data?.call;
  const messages = data?.messages;
  const shouldShowPlaceholder = !isLoading && !call;

  return (
    <div className="grid flex-1 min-h-0 gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="flex min-h-0 flex-col gap-4">
        {isLoading ? (
          <Skeleton className="h-32 w-full" />
        ) : shouldShowPlaceholder ? (
          <LandingPage />
        ) : (
          <CallDetails call={call} />
        )}
        <AiChatBox className="flex-1 min-h-0 h-full" isDisabled={isLoading || !call} />
      </div>
      <div className="hidden lg:block">
        <CallInsightsPanel call={call} messages={messages} />
      </div>
    </div>
  );
}
