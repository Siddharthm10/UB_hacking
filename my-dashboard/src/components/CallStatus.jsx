import React from 'react';

export default function CallStatus({ status, compact }) {
  const isGreen = status !== 'RED';
  const color = isGreen ? 'bg-emerald-100 text-emerald-700 ring-emerald-200' : 'bg-rose-100 text-rose-700 ring-rose-200';
  const text = isGreen ? 'Call Stable' : 'Alert Triggered';
  return (
    <span className={`inline-flex items-center gap-2 ${color} ring-1 px-2.5 py-1 rounded-full text-xs font-medium transition-colors`}>
      <span className={`w-2 h-2 rounded-full ${isGreen ? 'bg-emerald-500' : 'bg-rose-500'}`} />
      {!compact && text}
    </span>
  );
}

