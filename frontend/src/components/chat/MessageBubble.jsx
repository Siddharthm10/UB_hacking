import { cn } from '@/lib/utils';

export function MessageBubble({ role = 'assistant', content, streaming }) {
  const isUser = role === 'user';
  return (
    <div className={cn('flex w-full justify-center px-4')}>
      <div
        className={cn(
          'w-full max-w-3xl rounded-2xl border border-slate-800/70 px-5 py-4 shadow-sm shadow-black/40',
          isUser
            ? 'bg-slate-900/80 text-slate-100'
            : 'bg-slate-800/80 text-slate-100 backdrop-blur',
          streaming && 'ring-1 ring-primary/60'
        )}
      >
        <div className="whitespace-pre-line text-sm leading-7 text-slate-100">{content}</div>
      </div>
    </div>
  );
}
