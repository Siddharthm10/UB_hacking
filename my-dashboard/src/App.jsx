import React, { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Transcript from "./components/Transcript.jsx";
import { ShieldCheck } from "lucide-react";

export default function App() {
  const [call, setCall] = useState(null);
  const [messages, setMessages] = useState([]);
  const [isLive, setIsLive] = useState(true);

  useEffect(() => {
    document.title = "EthiCo Live";
  }, []);

  // Poll backend only when live
  useEffect(() => {
    if (!isLive) return;

    const base = import.meta?.env?.VITE_API_URL || "";
    let active = true;

    async function load() {
      try {
        const res = await fetch(`${base}/api/call/current`);
        if (!res.ok) return;
        const data = await res.json();
        if (!active) return;
        setCall(data);
        setMessages(data.transcript || []);
      } catch {
        // ignore in demo
      }
    }

    load();
    const id = setInterval(load, 3000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [isLive]);

  const handleStart = () => setIsLive(true);
  const handleStop = () => setIsLive(false);

  return (
    <div className="flex min-h-screen bg-gray-50 text-gray-900">
      {/* LEFT: Sidebar with Call Health */}
      <Sidebar call={call} />

      {/* RIGHT: Main */}
      <main className="flex-1 flex flex-col">
        {/* Top header */}
        <div className="flex items-center justify-between px-10 py-6 border-b border-gray-200 bg-white">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">Live Call</h1>
            <p className="text-xs text-gray-500 mt-1">
              EthiCo • Compliance &amp; Empathy Monitor
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleStart}
              className={`px-4 py-2 rounded-full text-xs font-semibold transition
                ${
                  isLive
                    ? "bg-emerald-500 text-white shadow-sm shadow-emerald-200"
                    : "border border-emerald-500 text-emerald-600 bg-white hover:bg-emerald-50"
                }`}
            >
              Start
            </button>

            <button
              onClick={handleStop}
              className={`px-4 py-2 rounded-full text-xs font-semibold transition
                ${
                  !isLive
                    ? "bg-red-500 text-white shadow-sm shadow-red-200"
                    : "border border-red-500 text-red-600 bg-white hover:bg-red-50"
                }`}
            >
              Stop
            </button>
          </div>
        </div>

        {/* Transcript area */}
        <div className="flex-1 px-10 py-6">
          <Transcript messages={messages} />
        </div>

        {/* Footer helper text */}
        <div className="px-10 pb-4 text-[10px] text-gray-400 flex items-center gap-2">
          <ShieldCheck size={12} className="text-emerald-500" />
          <span>
            Monitoring language for risk &amp; empathy. Start/Stop only controls
            analysis, not the underlying call.
          </span>
        </div>
      </main>
    </div>
  );
}
