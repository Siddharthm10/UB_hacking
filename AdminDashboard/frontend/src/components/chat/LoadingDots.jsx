export function LoadingDots() {
  return (
    <span className="flex items-center gap-1 text-slate-400">
      {[0, 1, 2].map((dot) => (
        <span
          key={dot}
          className="h-2 w-2 rounded-full bg-slate-500/60"
          style={{ animation: `pulse-dot 1.2s ease-in-out ${dot * 0.2}s infinite` }}
        />
      ))}
    </span>
  );
}
