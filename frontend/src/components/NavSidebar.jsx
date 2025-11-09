import React from "react";
import {
  Activity,
  ShieldCheck,
  HeadphonesIcon,
  History,
  Settings,
} from "lucide-react";

export default function NavSidebar() {
  return (
    <aside className="w-56 bg-slate-950 border-r border-slate-800 flex flex-col py-5 px-4 gap-6">
      {/* Logo */}
      <div className="flex items-center gap-2 px-1">
        <div className="w-7 h-7 rounded-xl bg-emerald-500/90 flex items-center justify-center text-xs font-bold text-slate-950">
          E
        </div>
        <div className="flex flex-col leading-tight">
          <span className="text-[11px] text-slate-400">EthiCo</span>
          <span className="text-xs font-semibold text-slate-100">
            Live Monitor
          </span>
        </div>
      </div>

      {/* Main nav */}
      <nav className="flex-1">
        <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500 px-1 mb-2">
          Overview
        </div>
        <NavItem icon={<Activity size={16} />} label="Live Calls" active />
        <NavItem icon={<HeadphonesIcon size={16} />} label="Agents" />
        <NavItem icon={<History size={16} />} label="Call History" />

        <div className="text-[9px] uppercase tracking-[0.16em] text-slate-500 px-1 mt-6 mb-2">
          Compliance
        </div>
        <NavItem icon={<ShieldCheck size={16} />} label="FDCPA Rules" />
        <NavItem icon={<Settings size={16} />} label="Settings" />
      </nav>

      {/* Bottom mini-profile */}
      <div className="mt-auto flex items-center gap-2 px-1">
        <div className="w-7 h-7 rounded-full bg-slate-800 flex items-center justify-center text-[9px] text-slate-300">
          OP
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] text-slate-200">Ops Console</span>
          <span className="text-[9px] text-slate-500">
            M&amp;T / Valmar Sandbox
          </span>
        </div>
      </div>
    </aside>
  );
}

function NavItem({ icon, label, active }) {
  return (
    <button
      className={`w-full flex items-center gap-2 px-2 py-2 rounded-xl text-[11px] mb-1 transition
        ${
          active
            ? "bg-emerald-500/10 text-emerald-400"
            : "text-slate-400 hover:bg-slate-900 hover:text-slate-100"
        }`}
    >
      <span className="text-slate-500">{icon}</span>
      <span>{label}</span>
      {active && (
        <span className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400" />
      )}
    </button>
  );
}
