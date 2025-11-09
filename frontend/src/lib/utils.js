import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs) {
  return twMerge(clsx(inputs));
}

export function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return '--';
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs.toString().padStart(2, '0')}s`;
}

export function formatDate(dateString) {
  if (!dateString) return '--';
  return new Date(dateString).toLocaleString();
}

export function sentimentPill(sentiment) {
  switch (sentiment) {
    case 'positive':
      return 'bg-emerald-500/15 text-emerald-200';
    case 'negative':
      return 'bg-rose-500/15 text-rose-200';
    case 'neutral':
    default:
      return 'bg-slate-500/20 text-slate-200';
  }
}
