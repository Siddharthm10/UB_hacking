import { cva } from 'class-variance-authority';
import { cn } from '@/lib/utils';

const badgeVariants = cva(
  'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium transition-colors',
  {
    variants: {
      variant: {
        default: 'bg-slate-700/70 text-slate-100',
        positive: 'bg-emerald-500/15 text-emerald-200',
        negative: 'bg-rose-500/15 text-rose-200',
        neutral: 'bg-slate-500/20 text-slate-200',
        outline: 'border border-slate-600/60 text-slate-200'
      }
    },
    defaultVariants: {
      variant: 'default'
    }
  }
);

export function Badge({ className, variant, children, ...props }) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {children}
    </span>
  );
}
