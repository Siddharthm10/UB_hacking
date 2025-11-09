import { StatCard } from '@/components/common/StatCard';
import { Activity, GaugeCircle, Shield } from 'lucide-react';

export function CallInsightsPanel({ call, messages }) {
  if (!call) {
    return (
      <div className="rounded-3xl border border-slate-900/50 bg-slate-950/30 p-4 text-sm text-slate-500">
        Metrics will appear once a call is selected.
      </div>
    );
  }

  const talkTurns = messages?.filter((msg) => msg.role === 'agent').length || 0;
  const listenTurns = messages?.filter((msg) => msg.role === 'customer').length || 0;
  const talkRatio = listenTurns ? (talkTurns / listenTurns).toFixed(2) : '1.0';
  const riskCount = call.riskFlags?.length || 0;

  return (
    <div className="grid gap-4">
      <StatCard label="Avg sentiment" value={call.sentiment || 'neutral'} trend="↑ 4%" trendLabel="vs. peers" icon={GaugeCircle} />
      <StatCard label="Risk flags" value={riskCount} trend="Watchlist" icon={Shield} />
      <StatCard label="Talk:Listen" value={talkRatio} icon={Activity} trend={`${talkTurns} / ${listenTurns} turns`} />
    </div>
  );
}
