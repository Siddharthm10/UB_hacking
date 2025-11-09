import React from "react";
import { PhoneCall, User, Clock3, AlertTriangle } from "lucide-react";

export default function Sidebar({ call, warnings = [], isCallActive }) {
  const duration = call?.durationSeconds || 0;
  const mins = Math.floor(duration / 60)
    .toString()
    .padStart(2, "0");
  const secs = (duration % 60).toString().padStart(2, "0");
  const warningCount = warnings.length;
  const hasWarnings = warningCount > 0;
  const healthLabel = hasWarnings
    ? "Action Needed"
    : isCallActive
    ? "Healthy"
    : "Idle";
  const healthDescription = hasWarnings
    ? "Review compliance alerts immediately."
    : isCallActive
    ? "No issues detected."
    : "Monitoring paused.";
  const pillClasses = hasWarnings
    ? "bg-red-50 border border-red-100 text-red-700 dark:bg-red-500/10 dark:border-red-500/30 dark:text-red-200"
    : isCallActive
    ? "bg-emerald-50 border border-emerald-100 text-emerald-700 dark:bg-emerald-500/10 dark:border-emerald-500/30 dark:text-emerald-200"
    : "bg-gray-100 border border-gray-200 text-gray-600 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-200";

  return (
    <aside className="w-80 bg-white border-r border-gray-200 dark:bg-slate-900 dark:border-slate-800 flex flex-col gap-6 px-6 py-6 text-gray-900 dark:text-slate-100">
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-2xl bg-emerald-500 flex items-center justify-center text-white font-semibold text-lg">
          E
        </div>
        <div className="flex flex-col leading-tight">
          <span className="font-semibold text-gray-900 dark:text-white">EthiCo Live</span>
          <span className="text-xs text-gray-500 dark:text-gray-400">Real-time Monitoring</span>
        </div>
      </div>

      <SidebarCard title="Call Details" icon={<PhoneCall size={16} />}>
        <Row label="Call ID" value={call?.callId || "—"} />
        <Row
          label="Status"
          value={
            call?.status
              ? call.status.replace("_", " ")
              : isCallActive
              ? "in progress"
              : "idle"
          }
        />
        <Row label="Agent" value={call?.agent?.name || "—"} />
        <Row label="Agent ID" value={call?.agent?.id || "—"} />
        <Row label="Duration" value={`${mins}:${secs}`} />
      </SidebarCard>

      <SidebarCard title="Customer" icon={<User size={16} />}>
        <Row label="Name" value={call?.customer?.name || "—"} />
        <Row label="Phone" value={call?.customer?.phone || "—"} />
        <Row label="Account" value={call?.customer?.accountId || "—"} />
        <Row label="Segment" value={call?.customer?.segment || "—"} />
      </SidebarCard>

      <div className="mt-auto">
        <div className="bg-white border border-gray-200 dark:bg-slate-900 dark:border-slate-800 rounded-2xl px-4 py-3 shadow-sm">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <Clock3 size={16} className="text-gray-400 dark:text-gray-500" />
              <span className="text-sm font-semibold text-gray-800 dark:text-slate-100">
                Call Health
              </span>
            </div>
            <div className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full ${pillClasses}`}>
              {hasWarnings ? (
                <AlertTriangle size={12} />
              ) : (
                <span className="w-1.5 h-1.5 rounded-full bg-current" />
              )}
              <span className="text-[10px] font-medium">{healthLabel}</span>
            </div>
          </div>

          <p className={`mt-1 text-xs font-medium ${hasWarnings ? "text-red-600" : "text-emerald-600"}`}>
            {healthDescription}
          </p>
          <p className="text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">
            {hasWarnings
              ? `${warningCount} active ${warningCount === 1 ? "alert" : "alerts"}.`
              : "Monitoring tone & language for compliance in real time."}
          </p>
        </div>
      </div>
    </aside>
  );
}

function SidebarCard({ title, icon, children }) {
  return (
    <div className="bg-white border border-gray-200 dark:bg-slate-900 dark:border-slate-800 rounded-2xl px-4 py-4 shadow-sm flex flex-col gap-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-slate-100">
        <span className="text-emerald-500">{icon}</span>
        <span>{title}</span>
      </div>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function Row({ label, value }) {
  return (
    <div className="flex justify-between items-baseline text-xs">
      <span className="text-gray-500 dark:text-gray-400">{label}</span>
      <span className="font-semibold text-gray-800 dark:text-slate-100 truncate">
        {value || "—"}
      </span>
    </div>
  );
}
