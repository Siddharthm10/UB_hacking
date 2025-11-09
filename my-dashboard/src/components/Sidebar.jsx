import React from "react";
import { PhoneCall, User, Clock3 } from "lucide-react";

export default function Sidebar({ call }) {
  const duration = call?.durationSeconds || 0;
  const mins = Math.floor(duration / 60).toString().padStart(2, "0");
  const secs = (duration % 60).toString().padStart(2, "0");

  return (
    <aside className="w-80 bg-white border-r border-gray-200 flex flex-col gap-6 px-6 py-6">
      {/* Brand */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded-2xl bg-emerald-500 flex items-center justify-center text-white font-semibold text-lg">
          E
        </div>
        <div className="flex flex-col leading-tight">
          <span className="font-semibold text-gray-900">EthiCo Live</span>
          <span className="text-xs text-gray-500">Real-time Monitoring</span>
        </div>
      </div>

      {/* Call Details */}
      <SidebarCard title="Call Details" icon={<PhoneCall size={16} />}>
        <Row label="Call ID" value={call?.callId || "CID-0001"} />
        <Row label="Agent" value={call?.agent?.name || "Alex Smith"} />
        <Row label="Agent ID" value={call?.agent?.id || "AG-1007"} />
        <Row label="Duration" value={`${mins}:${secs}`} />
      </SidebarCard>

      {/* Customer */}
      <SidebarCard title="Customer" icon={<User size={16} />}>
        <Row label="Name" value={call?.customer?.name || "Jane Doe"} />
        <Row
          label="Phone"
          value={call?.customer?.phone || "+1 (555) 123-4567"}
        />
        <Row
          label="Account"
          value={call?.customer?.accountId || "ACC-98765"}
        />
        <Row
          label="Segment"
          value={call?.customer?.segment || "Premium"}
        />
      </SidebarCard>

      {/* Call Health (bottom) */}
      <div className="mt-auto">
        <div className="bg-white border border-gray-200 rounded-2xl px-4 py-3 shadow-sm">
          <div className="flex items-center justify-between mb-1.5">
            <div className="flex items-center gap-2">
              <Clock3 size={16} className="text-gray-400" />
              <span className="text-sm font-semibold text-gray-800">
                Call Health
              </span>
            </div>

            {/* Status pill (purely informational) */}
            <div className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full bg-emerald-50 border border-emerald-100">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span className="text-[10px] font-medium text-emerald-700">
                Healthy
              </span>
            </div>
          </div>

          <p className="mt-1 text-xs font-medium text-emerald-600">
            No issues detected.
          </p>
          <p className="text-[10px] text-gray-500 mt-0.5">
            Monitoring tone &amp; language for compliance in real time.
          </p>
        </div>
      </div>
    </aside>
  );
}

function SidebarCard({ title, icon, children }) {
  return (
    <div className="bg-white border border-gray-200 rounded-2xl px-4 py-4 shadow-sm flex flex-col gap-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-gray-800">
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
      <span className="text-gray-500">{label}</span>
      <span className="font-semibold text-gray-800 truncate">
        {value}
      </span>
    </div>
  );
}
