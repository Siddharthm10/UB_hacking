import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchCallDetails } from '@/lib/api';
import { useCallStore } from '@/state/useCallStore';
import { CallDetails } from '@/components/calls/CallDetails';
import { CallInsightsPanel } from '@/components/calls/CallInsightsPanel';
import { AiChatBox } from '@/components/chat/AiChatBox';
import { Skeleton } from '@/components/common/Skeleton';

export function DashboardPage({ agentId, callIdFromRoute }) {
  const {
    selectedCallId,
    setSelectedCallId,
    agentId: storeAgent,
    setAgentId
  } = useCallStore();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

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

  useEffect(() => {
    if (!callIdFromRoute && agentId && !selectedCallId) {
      const cached = queryClient.getQueryData(['agent', agentId, 'calls']);
      const firstCall = cached?.pages?.[0]?.items?.[0];
      if (firstCall) {
        setSelectedCallId(firstCall.callId);
        navigate(`/a/${agentId}/c/${firstCall.callId}`, { replace: true });
      }
    }
  }, [agentId, callIdFromRoute, navigate, queryClient, selectedCallId, setSelectedCallId]);

  const activeCallId = callIdFromRoute || selectedCallId;

  const { data, isLoading } = useQuery({
    queryKey: ['call', activeCallId],
    queryFn: () => fetchCallDetails(activeCallId),
    enabled: Boolean(activeCallId)
  });

  const call = data?.call;
  const messages = data?.messages;

  return (
    <div className="grid flex-1 min-h-0 gap-4 lg:grid-cols-[minmax(0,1fr)_320px]">
      <div className="flex min-h-0 flex-col gap-4">
        {isLoading ? <Skeleton className="h-32 w-full" /> : <CallDetails call={call} />}
        <AiChatBox className="flex-1 min-h-0 h-full" isDisabled={isLoading || !call} />
      </div>
      <div className="hidden lg:block">
        <CallInsightsPanel call={call} messages={messages} />
      </div>
    </div>
  );
}
