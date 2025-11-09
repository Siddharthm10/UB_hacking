import { cn, formatDate } from '@/lib/utils';

export function TranscriptMessage({ message }) {
  const alignment = message.role === 'agent' ? 'items-end' : 'items-start';
  const bubbleTone =
    message.role === 'agent'
      ? 'bg-primary/15 text-primary-foreground border border-primary/40'
      : 'bg-slate-800/80 text-slate-100 border border-slate-700/60';

  return (
    <div className={cn('flex flex-col gap-1 px-4', alignment)}>
      <div className="text-xs uppercase tracking-wide text-slate-500">
        {message.role} • {formatDate(message.ts)}
      </div>
      <div
        className={cn(
          'max-w-2xl rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-lg shadow-black/40',
          bubbleTone
        )}
      >
        {message.text}
      </div>
    </div>
  );
}
