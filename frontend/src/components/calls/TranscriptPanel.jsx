import { useEffect, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { TranscriptMessage } from './TranscriptMessage';

export function TranscriptPanel({ messages = [] }) {
  const parentRef = useRef(null);
  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 110,
    overscan: 6
  });

  useEffect(() => {
    const el = parentRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages.length]);

  return (
    <div ref={parentRef} className="flex-1 overflow-y-auto rounded-3xl border border-slate-900/60 bg-slate-950/60">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          position: 'relative'
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const message = messages[virtualRow.index];
          return (
            <div
              key={`${message.callId}-${message.turn}`}
              className="absolute top-0 left-0 w-full"
              style={{
                transform: `translateY(${virtualRow.start}px)`
              }}
            >
              <TranscriptMessage message={message} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
