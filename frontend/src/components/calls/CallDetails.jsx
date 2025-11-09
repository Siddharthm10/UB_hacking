import { AlertTriangle, Clock3, UserCircle2 } from 'lucide-react';
import { formatDate, formatDuration, sentimentPill, cn } from '@/lib/utils';
import { Badge } from '@/components/common/Badge';
import { Pill } from '@/components/common/Pill';

export function CallDetails({ call }) {
  if (!call) {
    return (
      <div className="flex h-32 flex-col justify-center rounded-2xl border border-slate-800 bg-slate-900/40 px-6">
        <p className="text-sm text-slate-500">Select a call to view transcript and insights.</p>
      </div>
    );
  }

  return (
    <div className="rounded-3xl border border-slate-800/60 bg-slate-900/50 p-6 shadow-inner shadow-black/30">
      <div className="flex flex-wrap items-center gap-4">
        <div>
          <p className="text-xs uppercase tracking-wide text-slate-500">Call header</p>
          <h2 className="text-2xl font-semibold text-slate-50">{call.header}</h2>
        </div>
        {call.sentiment ? (
          <Badge className={cn('capitalize', sentimentPill(call.sentiment))}>{call.sentiment}</Badge>
        ) : null}
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4 text-sm text-slate-300 md:grid-cols-4">
        <div className="flex items-center gap-2">
          <Clock3 size={16} className="text-slate-400" />
          {formatDuration(call.durationSec)}
        </div>
        <div className="flex items-center gap-2">
          <UserCircle2 size={16} className="text-slate-400" />
          {call.agentId}
        </div>
        <div>{formatDate(call.startedAt)}</div>
        <div className="flex items-center gap-2 text-amber-200">
          <AlertTriangle size={14} />
          {call.riskFlags?.length || 0} risk flags
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {call.riskFlags?.map((flag) => (
          <Pill
            key={flag.code}
            label={`${flag.label} • ${flag.severity}`}
            tone={flag.severity === 'high' ? 'danger' : flag.severity === 'med' ? 'warning' : 'default'}
          />
        ))}
      </div>
    </div>
  );
}
