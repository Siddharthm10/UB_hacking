import React, { useEffect, useState } from "react";
import Sidebar from "./components/Sidebar.jsx";
import Transcript from "./components/Transcript.jsx";

export default function App() {
  const [call, setCall] = useState(null);
  const [messages, setMessages] = useState([]);
  const [status, setStatus] = useState("GREEN");
  const [isLive, setIsLive] = useState(true);

  useEffect(() => {
    document.title = "EthiCo Live";
  }, []);

  // Poll backend only when monitoring is live
  useEffect(() => {
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
        setStatus(data.status || "GREEN");
      } catch {
        // silent for demo
      }
    }

    if (isLive) {
      load();
      const id = setInterval(load, 3000);
      return () => {
        active = false;
        clearInterval(id);
      };
    }

    return () => {
      active = false;
    };
  }, [isLive]);

  // Smooth duration ticking while live
  useEffect(() => {
    if (!call || !isLive) return;
    const t = setInterval(() => {
      setCall((c) =>
        c
          ? { ...c, durationSeconds: (c.durationSeconds || 0) + 1 }
          : c
      );
    }, 1000);
    return () => clearInterval(t);
  }, [call?.callId, isLive]);

  const handleStart = () => setIsLive(true);
  const handleStop = () => setIsLive(false);

  return (
    <div className="flex h-screen w-full bg-gray-50 text-gray-900">
      {/* Sidebar: details + Call Health card */}
      <Sidebar call={call} status={status} />

      {/* Main area */}
      <main className="flex-1 flex flex-col">
        <header className="px-6 py-4 border-b border-gray-200 bg-white/70 backdrop-blur-sm flex items-center justify-between">
          <div className="text-lg font-semibold tracking-tight">
            Live Call
          </div>
          <div className="flex items-center gap-4">
            <div className="text-sm text-gray-500">
              EthiCo • Compliance & Empathy Monitor
            </div>
            {/* Start / Stop buttons in top-right */}
            <div className="flex gap-2">
              <button
                onClick={handleStart}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold transition ${
                  isLive
                    ? "bg-emerald-500 text-white shadow-sm"
                    : "bg-emerald-50 text-emerald-700 hover:bg-emerald-100"
                }`}
              >
                Start
              </button>
              <button
                onClick={handleStop}
                className={`px-4 py-1.5 rounded-full text-xs font-semibold transition ${
                  !isLive
                    ? "bg-red-500 text-white shadow-sm"
                    : "bg-red-50 text-red-600 hover:bg-red-100"
                }`}
              >
                Stop
              </button>
            </div>
          </div>
        </header>

        {/* Transcript area */}
        <Transcript messages={messages} status={status} isLive={isLive} />
      </main>
    </div>
  );
}
