import React from "react";
import { AlertTriangle } from "lucide-react";

export default function WarningsPanel({ warnings = [] }) {
  return (
    <div className="bg-white border border-gray-200 dark:bg-slate-900 dark:border-slate-800 rounded-2xl px-4 py-4 shadow-sm flex flex-col gap-4 max-h-[28rem]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm font-semibold text-gray-800 dark:text-slate-100">
          <AlertTriangle size={16} className="text-red-500" />
          <span>Compliance Alerts</span>
        </div>
        <span className="text-xs text-gray-400 dark:text-gray-500">
          {warnings.length} active
        </span>
      </div>
      <div className="space-y-3 overflow-y-auto pr-1">
        {warnings.length === 0 && (
          <p className="text-sm text-gray-400 dark:text-gray-500 italic">
            No warnings triggered.
          </p>
        )}
        {warnings.map((warning, idx) => (
          <article
            key={`${warning.rule || "rule"}-${idx}`}
            className="border border-gray-200 dark:border-slate-700 rounded-xl p-3 text-xs space-y-1 bg-gray-50 dark:bg-slate-800"
          >
            <div className="flex items-center justify-between text-[11px] font-semibold">
              <span className="uppercase tracking-wide text-gray-500 dark:text-gray-400">
                {warning.level || warning.type || "WARNING"}
              </span>
              <span className="text-gray-400 dark:text-gray-500">
                {warning.rule || "FDCPA"}
              </span>
            </div>
            <p className="text-gray-800 dark:text-slate-100">{warning.text || warning.excerpt}</p>
            {warning.suggestion_agent && (
              <p className="text-gray-500 dark:text-gray-400">
                <span className="font-semibold">Suggestion: </span>
                {warning.suggestion_agent}
              </p>
            )}
          </article>
        ))}
      </div>
    </div>
  );
}
