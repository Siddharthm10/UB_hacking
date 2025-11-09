import { useEffect, useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useCallStore } from '@/state/useCallStore';
import { cn, formatDate } from '@/lib/utils';

export function CommandPalette({ calls = [], onSelect }) {
  const { commandPaletteOpen, setCommandPaletteOpen } = useCallStore();
  const [query, setQuery] = useState('');

  useEffect(() => {
    function handleKey(event) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setCommandPaletteOpen(!commandPaletteOpen);
      }
      if (commandPaletteOpen && event.key === 'Escape') {
        setCommandPaletteOpen(false);
      }
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [commandPaletteOpen, setCommandPaletteOpen]);

  useEffect(() => {
    if (!commandPaletteOpen) {
      setQuery('');
    }
  }, [commandPaletteOpen]);

  const filtered = useMemo(() => {
    if (!query) return calls;
    return calls.filter((call) => call.header.toLowerCase().includes(query.toLowerCase()));
  }, [calls, query]);

  return (
    <AnimatePresence>
      {commandPaletteOpen ? (
        <motion.div
          className="fixed inset-0 z-50 flex items-start justify-center bg-black/60 px-4 py-20 backdrop-blur-sm"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={() => setCommandPaletteOpen(false)}
        >
          <motion.div
            className="w-full max-w-2xl rounded-2xl border border-slate-700/80 bg-slate-900/90 p-4 shadow-2xl"
            initial={{ y: 40, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 20, opacity: 0 }}
            onClick={(e) => e.stopPropagation()}
          >
            <input
              autoFocus
              className="w-full rounded-xl border border-slate-700/80 bg-slate-900 px-3 py-2 text-slate-100 outline-none focus:border-primary/60"
              placeholder="Search calls..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
            <div className="mt-3 max-h-64 overflow-y-auto">
              {filtered.map((call) => (
                <button
                  key={call.callId}
                  className={cn(
                    'flex w-full flex-col gap-1 rounded-xl px-3 py-2 text-left text-sm text-slate-200 hover:bg-slate-800/70'
                  )}
                  onClick={() => {
                    onSelect(call.callId);
                    setCommandPaletteOpen(false);
                  }}
                >
                  <span className="font-medium">{call.header}</span>
                  <span className="text-xs text-slate-400">{formatDate(call.startedAt)}</span>
                </button>
              ))}
              {!filtered.length ? (
                <p className="py-6 text-center text-sm text-slate-500">No calls match that search.</p>
              ) : null}
            </div>
            <div className="mt-4 flex justify-between text-xs text-slate-500">
              <span>Enter to open • Esc to close</span>
              <span>Cmd + K</span>
            </div>
          </motion.div>
        </motion.div>
      ) : null}
    </AnimatePresence>
  );
}
