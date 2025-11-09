import { useState } from 'react';
import { Sidebar } from './Sidebar';
import { Menu } from 'lucide-react';
import { cn } from '@/lib/utils';

export function ChatShell({ children }) {
  const [mobileVisible, setMobileVisible] = useState(false);
  return (
    <div className="flex h-screen w-full bg-slate-950 text-slate-100">
      <Sidebar mobileVisible={mobileVisible} setMobileVisible={setMobileVisible} />
      <div className="flex flex-1 flex-col overflow-hidden">
        <div className="flex items-center gap-3 border-b border-slate-900/70 px-4 py-3 sm:hidden">
          <button
            className="rounded-full border border-slate-800/70 p-2 text-slate-200"
            onClick={() => setMobileVisible(true)}
            aria-label="Toggle sidebar"
          >
            <Menu size={18} />
          </button>
          <div>
            <p className="text-xs uppercase tracking-wider text-slate-500">Call Review</p>
            <p className="text-sm font-semibold text-slate-100">Dashboard</p>
          </div>
        </div>
        <main className={cn('flex flex-1 min-h-0 flex-col gap-4 overflow-hidden p-4 md:p-6')}>
          {children}
        </main>
      </div>
    </div>
  );
}
