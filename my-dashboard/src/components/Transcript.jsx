import React, { useRef, useEffect } from "react";
import { Bot, User } from "lucide-react";

export default function Transcript({ messages, status, isLive }) {
  const ref = useRef(null);

  useEffect(() => {
    if (ref.current) {
      ref.current.scrollTop = ref.current.scrollHeight;
    }
  }, [messages]);

  return (
    <section className="flex-1 flex flex-col px-6 py-4 gap-4">
      <div className="flex items-baseline gap-2">
        <h2 className="text-sm font-semibold text-gray-800">
          Live Transcript
        </h2>
        <span className="text-[10px] text-gray-400">
          {isLive ? "Monitoring" : "Paused"}
        </span>
      </div>

      <div
        ref={ref}
        className="flex-1 bg-white rounded-xl shadow-sm border border-gray-200 p-4 overflow-y-auto space-y-3"
      >
        {(!messages || messages.length === 0) && (
          <p className="text-xs text-gray-400 italic">
            {isLive
              ? "Waiting for transcript from EthiCo backend..."
              : "Monitoring paused. Press Start to resume."}
          </p>
        )}

        {messages.map((m, i) => (
          <Bubble key={i} speaker={m.speaker} text={m.text} />
        ))}
      </div>
    </section>
  );
}

function Bubble({ speaker, text }) {
  const isAgent = speaker === "agent";
  const alignClass = isAgent ? "justify-start" : "justify-end";
  const bubbleClass = isAgent
    ? "bg-gray-100 text-gray-800 rounded-tl-none"
    : "bg-blue-600 text-white rounded-br-none";
  const Icon = isAgent ? Bot : User;
  const avatarClass = isAgent
    ? "bg-blue-100 text-blue-700"
    : "bg-gray-200 text-gray-700";

  return (
    <div className={`flex items-end gap-2 ${alignClass}`}>
      {isAgent && (
        <div
          className={`w-7 h-7 rounded-full ${avatarClass} flex items-center justify-center text-xs`}
        >
          <Icon size={14} />
        </div>
      )}
      <div
        className={`max-w-[75%] px-3 py-2 rounded-xl text-xs leading-snug ${bubbleClass}`}
      >
        {text}
      </div>
      {!isAgent && (
        <div
          className={`w-7 h-7 rounded-full ${avatarClass} flex items-center justify-center text-xs`}
        >
          <Icon size={14} />
        </div>
      )}
    </div>
  );
}
