import { cn } from '@/lib/utils';

export function Pill({ label, tone = 'default', className }) {
  const tones = {
    default: 'bg-slate-700/50 text-slate-200',
    success: 'bg-emerald-600/20 text-emerald-200',
    warning: 'bg-amber-500/20 text-amber-100',
    danger: 'bg-rose-600/20 text-rose-100'
  };
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full px-3 py-1 text-xs font-medium',
        tones[tone],
        className
      )}
    >
      {label}
    </span>
  );
}
