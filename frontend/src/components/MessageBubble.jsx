import React from 'react';
import { User, Bot } from 'lucide-react';

export default function MessageBubble({ speaker, text }) {
  const isAgent = speaker === 'agent';
  return (
    <div className={`flex items-start gap-3 ${isAgent ? 'justify-start' : 'justify-end'}`}>
      {isAgent && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center">
          <Bot size={16} />
        </div>
      )}
      <div className={`max-w-[75%] p-3 rounded-lg shadow-sm ${isAgent ? 'bg-gray-100 text-gray-800 rounded-tl-none' : 'bg-blue-600 text-white rounded-br-none'}`}>
        <p className="text-sm leading-relaxed">{text}</p>
      </div>
      {!isAgent && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 text-gray-700 flex items-center justify-center">
          <User size={16} />
        </div>
      )}
    </div>
  );
}

