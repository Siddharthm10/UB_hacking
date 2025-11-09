import { cn } from '@/lib/utils';

export function StatCard({ label, value, trend, trendLabel, icon: Icon, className }) {
  return (
    <div
      className={cn(
        'rounded-2xl border border-slate-800/60 bg-slate-900/60 p-4 shadow-inner shadow-black/20',
        className
      )}
    >
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-slate-400">
        {Icon ? <Icon size={16} className="text-slate-400" /> : null}
        {label}
      </div>
      <div className="mt-2 text-2xl font-semibold text-slate-50">{value}</div>
      {trend ? (
        <div className="mt-1 text-xs text-slate-400">
          {trend}{' '}
          <span className="text-slate-500">
            {trendLabel}
          </span>
        </div>
      ) : null}
    </div>
  );
}
