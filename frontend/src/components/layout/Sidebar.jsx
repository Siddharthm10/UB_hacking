import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useMatch } from 'react-router-dom';
import { useInfiniteQuery } from '@tanstack/react-query';
import { Command, Search, Sparkles } from 'lucide-react';
import { fetchAgentCalls } from '@/lib/api';
import { useCallStore } from '@/state/useCallStore';
import { CallListItem } from '@/components/calls/CallListItem';
import { CommandPalette } from './CommandPalette';
import { cn } from '@/lib/utils';

export function Sidebar({ mobileVisible, setMobileVisible = () => {} }) {
  const {
    agentId,
    setAgentId,
    selectedCallId,
    setSelectedCallId,
    sidebarOpen,
    setCommandPaletteOpen
  } = useCallStore();
  const [input, setInput] = useState(agentId || '');
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const navigate = useNavigate();
  const callRouteMatch = useMatch('/a/:agentId/c/:callId');
  const [highlightIndex, setHighlightIndex] = useState(0);

  useEffect(() => {
    setInput(agentId || '');
  }, [agentId]);

  const handleAgentSearch = () => {
    const nextAgent = input.trim();
    if (!nextAgent) {
      setSelectedCallId(null);
      setAgentId('');
      return;
    }
    if (nextAgent === agentId) return;
    setSelectedCallId(null);
    setAgentId(nextAgent);
    navigate(`/a/${nextAgent}`, { replace: false });
  };

  const handleAgentSubmit = (event) => {
    event.preventDefault();
    handleAgentSearch();
  };

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetching,
    isFetchingNextPage
  } = useInfiniteQuery({
    queryKey: ['agent', agentId, 'calls'],
    queryFn: ({ pageParam }) => fetchAgentCalls({ agentId, cursor: pageParam }),
    enabled: Boolean(agentId),
    getNextPageParam: (lastPage) => lastPage?.nextCursor ?? undefined
  });

  const calls = useMemo(() => {
    return data?.pages.flatMap((page) => page.items) ?? [];
  }, [data]);

  const hasCallInRoute = Boolean(callRouteMatch?.params?.callId);

  useEffect(() => {
    if (!agentId || selectedCallId || !calls.length || hasCallInRoute) return;
    const firstCallId = calls[0]?.callId;
    if (!firstCallId) return;
    setSelectedCallId(firstCallId);
    navigate(`/a/${agentId}/c/${firstCallId}`, { replace: true });
  }, [agentId, calls, hasCallInRoute, navigate, selectedCallId, setSelectedCallId]);

  useEffect(() => {
    setHighlightIndex(0);
  }, [calls.length]);

  useEffect(() => {
    if (!selectedCallId) return;
    const idx = calls.findIndex((call) => call.callId === selectedCallId);
    if (idx >= 0) {
      setHighlightIndex(idx);
    }
  }, [calls, selectedCallId]);

  const handleScroll = () => {
    const el = listRef.current;
    if (!el || !hasNextPage || isFetchingNextPage) return;
    if (el.scrollTop + el.clientHeight >= el.scrollHeight - 64) {
      fetchNextPage({ pageParam: data?.pages.at(-1)?.nextCursor });
    }
  };

  const handleSelect = (callId) => {
    if (!callId) return;
    setSelectedCallId(callId);
    if (agentId) {
      navigate(`/a/${agentId}/c/${callId}`);
    }
    setMobileVisible(false);
  };

  useEffect(() => {
    function onKey(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setCommandPaletteOpen(true);
        return;
      }
      const searchFocused = document.activeElement === inputRef.current;
      if (event.key === '/' && !searchFocused) {
        event.preventDefault();
        inputRef.current?.focus();
        return;
      }
      if (searchFocused && ['j', 'k', 'ArrowDown', 'ArrowUp', 'Enter'].includes(event.key)) {
        return;
      }
      if (!calls.length) return;
      if (event.key === 'j' || event.key === 'ArrowDown') {
        event.preventDefault();
        setHighlightIndex((idx) => Math.min(idx + 1, calls.length - 1));
      }
      if (event.key === 'k' || event.key === 'ArrowUp') {
        event.preventDefault();
        setHighlightIndex((idx) => Math.max(idx - 1, 0));
      }
      if (event.key === 'Enter') {
        const call = calls[highlightIndex];
        if (call) handleSelect(call.callId);
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [calls, highlightIndex, setCommandPaletteOpen]);

  const sidebarBody = (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-600">Agent</p>
          <h1 className="text-lg font-semibold text-slate-100">Call Review</h1>
        </div>
        <button
          className="rounded-full border border-slate-700/80 p-2 text-slate-400 hover:text-slate-100"
          onClick={() => setCommandPaletteOpen(true)}
          aria-label="Open command palette"
        >
          <Command size={16} />
        </button>
      </div>

      <form
        onSubmit={handleAgentSubmit}
        className="mt-4 rounded-2xl border border-slate-800/80 bg-slate-900/60 px-3 py-2 focus-within:border-primary/60"
      >
        <div className="flex items-center gap-2 text-slate-500">
          <Search size={16} />
          <input
            ref={inputRef}
            className="w-full bg-transparent text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none"
            placeholder="Enter agent ID…"
            value={input}
            onChange={(e) => setInput(e.target.value)}
          />
          <span className="rounded-md bg-slate-800 px-1 text-[10px] uppercase tracking-wide text-slate-400">
            /
          </span>
        </div>
      </form>

      <div ref={listRef} onScroll={handleScroll} className="mt-4 flex-1 space-y-2 overflow-y-auto pr-1">
        {!agentId && (
          <div className="rounded-2xl border border-dashed border-slate-800/80 p-4 text-sm text-slate-500">
            Start by entering an agent ID. Use Cmd + K to jump.
          </div>
        )}
        {calls.map((call, idx) => (
          <CallListItem
            key={call.callId}
            call={call}
            selected={selectedCallId === call.callId}
            highlighted={idx === highlightIndex}
            onClick={() => handleSelect(call.callId)}
          />
        ))}
        {isFetchingNextPage ? (
          <div className="py-4 text-center text-xs text-slate-500">Loading more calls…</div>
        ) : null}
        {agentId && !isFetching && !calls.length ? (
          <div className="rounded-2xl border border-dashed border-slate-800/80 p-4 text-sm text-slate-500">
            No calls found for that agent.
          </div>
        ) : null}
      </div>

      <div className="rounded-2xl border border-slate-800/70 bg-gradient-to-br from-slate-900 via-slate-900 to-slate-800 p-4 text-sm text-slate-300">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-primary">
          <Sparkles size={14} />
          AI Helper
        </div>
        <p className="mt-2 text-xs text-slate-400">
          Ask anything about the transcript or compliance risks.
        </p>
      </div>
    </div>
  );

  return (
    <>
      <aside
        className={cn(
          'hidden border-r border-slate-900/60 bg-slate-950/90 p-4 sm:flex sm:flex-col',
          sidebarOpen ? 'w-72 lg:w-80' : 'w-20'
        )}
      >
        {sidebarBody}
      </aside>
      {mobileVisible ? (
        <>
          <div className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm sm:hidden" onClick={() => setMobileVisible(false)} />
          <div className="fixed inset-y-0 left-0 z-50 w-72 overflow-y-auto border-r border-slate-900/60 bg-slate-950/95 p-4 sm:hidden">
            {sidebarBody}
          </div>
        </>
      ) : null}
      <CommandPalette calls={calls} onSelect={handleSelect} />
    </>
  );
}
