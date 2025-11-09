import { motion } from 'framer-motion';
import { cn, formatDate, formatDuration, sentimentPill } from '@/lib/utils';
import { Badge } from '@/components/common/Badge';

export function CallListItem({ call, selected, highlighted, onClick }) {
  return (
    <motion.button
      layout
      onClick={onClick}
      className={cn(
        'group w-full rounded-xl border px-3 py-3 text-left transition',
        selected
          ? 'bg-slate-800/80 border-slate-700 shadow-md shadow-black/50'
          : 'border-transparent hover:bg-slate-900/40',
        highlighted && !selected ? 'border-primary/50' : null
      )}
    >
      <div className="flex items-center justify-between text-xs font-medium text-slate-400">
        <span>{formatDate(call.startedAt)}</span>
        <span>{formatDuration(call.durationSec)}</span>
      </div>
      <p className="mt-2 line-clamp-2 text-sm font-semibold text-slate-100">{call.header}</p>
      <div className="mt-3 flex flex-wrap gap-2">
        {call.sentiment ? (
          <Badge className={cn('capitalize', sentimentPill(call.sentiment))}>{call.sentiment}</Badge>
        ) : null}
        {call.riskFlags?.slice(0, 2).map((flag) => (
          <Badge key={flag.code} variant="outline" className="text-amber-200 border-amber-400/40">
            {flag.label}
          </Badge>
        ))}
      </div>
    </motion.button>
  );
}
