import React from "react";
import { Phone, User, Clock } from "lucide-react";

export default function Sidebar({ call, status }) {
  const duration = call?.durationSeconds || 0;
  const mins = Math.floor(duration / 60).toString().padStart(2, "0");
  const secs = (duration % 60).toString().padStart(2, "0");

  return (
    <aside className="w-80 h-full border-r border-gray-200 bg-white flex flex-col">
      {/* Brand */}
      <div className="px-5 py-4 border-b border-gray-200">
        <div className="text-xs font-semibold tracking-[0.18em] text-gray-500 uppercase">
          EthiCo Live
        </div>
        <div className="text-[10px] text-gray-400">
          Real-time Monitoring
        </div>
      </div>

      {/* Call Details */}
      <div className="px-5 py-4 space-y-4 text-sm">
        <SectionLabel>Call Details</SectionLabel>
        {call ? (
          <>
            <Row
              icon={<Phone size={14} />}
              label="Call ID"
              value={call.callId}
            />
            <Row
              icon={<User size={14} />}
              label="Agent"
              value={call.agent?.name}
            />
            <Row
              icon={<User size={14} />}
              label="Agent ID"
              value={call.agent?.id}
            />
            <Row
              icon={<Clock size={14} />}
              label="Duration"
              value={`${mins}:${secs}`}
            />
          </>
        ) : (
          <div className="text-xs text-gray-400">
            Loading active call...
          </div>
        )}
      </div>

      {/* Customer */}
      {call?.customer && (
        <div className="px-5 py-4 border-t border-gray-100 space-y-2 text-xs">
        <SectionLabel>Customer</SectionLabel>
          <Detail label="Name" value={call.customer.name} />
          <Detail label="Phone" value={call.customer.phone} />
          <Detail label="Account" value={call.customer.accountId} />
          <Detail
            label="Segment"
            value={call.customer.segment || "Premium"}
          />
        </div>
      )}

      {/* Call Health card (like screenshot) */}
      <div className="px-5 py-4 border-t border-gray-100">
        <SectionLabel>Call Health</SectionLabel>
        <CallHealthPill status={status} />
      </div>

      {/* Bottom hint */}
      <div className="mt-auto px-5 py-4 border-t border-gray-200 text-[10px] text-gray-500">
        Monitoring language for risk & empathy in real time. Use Start / Stop
        to control live analysis without closing the dashboard.
      </div>
    </aside>
  );
}

/* Helpers */

function SectionLabel({ children }) {
  return (
    <div className="text-[10px] font-semibold uppercase tracking-wide text-gray-500 mb-2">
      {children}
    </div>
  );
}

function Row({ icon, label, value }) {
  if (!value) return null;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-400">{icon}</span>
      <span className="text-gray-500">{label}:</span>
      <span className="font-semibold text-gray-900 truncate">
        {value}
      </span>
    </div>
  );
}

function Detail({ label, value }) {
  if (!value) return null;
  return (
    <div className="flex justify-between gap-2">
      <span className="text-gray-400">{label}</span>
      <span className="font-medium text-gray-900 truncate">
        {value}
      </span>
    </div>
  );
}

/* Call Health pill styled like screenshot */
function CallHealthPill({ status }) {
  let label = "No issues detected.";
  let pillText = "On";
  let pillBg = "bg-emerald-500";
  let pillTextColor = "text-white";
  let textColor = "text-emerald-600";

  if (status === "YELLOW") {
    label = "Caution: review language.";
    pillText = "On";
    pillBg = "bg-amber-400";
    textColor = "text-amber-600";
  } else if (status === "RED") {
    label = "At Risk: potential violation.";
    pillText = "Alert";
    pillBg = "bg-red-500";
    textColor = "text-red-600";
  }

  return (
    <div className="w-full rounded-2xl border border-gray-100 bg-white shadow-sm px-3 py-3 flex flex-col gap-1">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs text-gray-700">
          <span className="w-4 h-4 rounded-full border border-gray-300 flex items-center justify-center text-[9px] text-gray-500">
            ○
          </span>
          <span className="font-medium">Call Health</span>
        </div>
        <div
          className={`flex items-center gap-1 px-2 py-0.5 rounded-full text-[9px] font-semibold ${pillBg} ${pillTextColor}`}
        >
          <span className="w-1.5 h-1.5 rounded-full bg-white" />
          <span>{pillText}</span>
        </div>
      </div>
      <div className={`text-[10px] ${textColor}`}>{label}</div>
    </div>
  );
}
