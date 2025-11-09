import React, { useEffect, useRef } from "react";
import { Bot, User } from "lucide-react";

export default function Transcript({ messages }) {
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  return (
    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex flex-col h-full">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-100 flex items-center gap-2">
        <span className="text-gray-800 font-semibold text-base">
          Live Transcript
        </span>
        <span className="text-xs text-gray-400">Monitoring</span>
      </div>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto px-6 py-4 space-y-4 bg-gray-50"
      >
        {(!messages || messages.length === 0) && (
          <p className="text-sm text-gray-400 italic">
            Connecting to live transcript...
          </p>
        )}

        {messages.map((m, i) => (
          <TranscriptLine
            key={i}
            speaker={m.speaker}
            text={m.text}
          />
        ))}
      </div>
    </div>
  );
}

function TranscriptLine({ speaker, text }) {
  const isAgent = speaker === "agent";

  const bubbleBase =
    "max-w-[60%] px-4 py-2.5 rounded-2xl text-sm leading-snug shadow-sm";

  const agentBubble = `${bubbleBase} bg-white text-gray-800 rounded-tl-none border border-gray-200`;
  const customerBubble = `${bubbleBase} bg-blue-600 text-white rounded-br-none`;

  return (
    <div
      className={`flex items-end gap-3 ${
        isAgent ? "justify-start" : "justify-end"
      }`}
    >
      {isAgent && (
        <div className="w-8 h-8 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center">
          <Bot size={16} />
        </div>
      )}

      <div className={isAgent ? agentBubble : customerBubble}>{text}</div>

      {!isAgent && (
        <div className="w-8 h-8 rounded-full bg-gray-200 text-gray-700 flex items-center justify-center">
          <User size={16} />
        </div>
      )}
    </div>
  );
}
