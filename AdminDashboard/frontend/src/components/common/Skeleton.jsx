import { cn } from '@/lib/utils';

export function Skeleton({ className }) {
  return <div className={cn('animate-pulse rounded-xl bg-slate-800/60', className)} />;
}
