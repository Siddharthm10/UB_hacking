import { Sparkles } from 'lucide-react';

export default function LandingPage() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center rounded-3xl border border-dashed border-slate-800/70 bg-slate-950/30 text-center">
      <Sparkles size={32} className="text-primary" />
      <h2 className="mt-4 text-2xl font-semibold text-slate-50">ChatGPT-style Call Review</h2>
      <p className="mt-2 max-w-lg text-sm text-slate-400">
        Search for an agent on the left sidebar to load recent calls. Select a call to explore the
        transcript, then ask the AI assistant for summaries, risks, or compliance insights.
      </p>
      <div className="mt-6 flex flex-wrap justify-center gap-2 text-xs text-slate-400">
        <span className="rounded-full border border-slate-800/60 px-3 py-1">Cmd + K</span>
        <span className="rounded-full border border-slate-800/60 px-3 py-1">/ focus search</span>
        <span className="rounded-full border border-slate-800/60 px-3 py-1">J / K navigate</span>
      </div>
    </div>
  );
}
