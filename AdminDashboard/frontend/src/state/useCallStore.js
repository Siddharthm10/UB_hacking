import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { nanoid } from 'nanoid';

const defaultPrompts = [
  'Summarize this call',
  'List payment amounts mentioned',
  'What FDCPA risks exist?',
  'What are the action items?'
];

export const useCallStore = create(
  persist(
    (set, get) => ({
      agentId: '',
      selectedCallId: null,
      sidebarOpen: true,
      drawerOpen: true,
      commandPaletteOpen: false,
      aiChats: {},
      setAgentId: (agentId) => set({ agentId }),
      setSelectedCallId: (selectedCallId) => set({ selectedCallId }),
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      toggleDrawer: () => set((state) => ({ drawerOpen: !state.drawerOpen })),
      setCommandPaletteOpen: (commandPaletteOpen) => set({ commandPaletteOpen }),
      addAiMessage: (callId, message) =>
        set((state) => {
          if (!callId) return state;
          const thread = state.aiChats[callId] ?? [];
          const nextMessage = { id: message.id || nanoid(), ...message };
          return {
            aiChats: {
              ...state.aiChats,
              [callId]: [...thread, nextMessage]
            }
          };
        }),
      updateAiMessage: (callId, id, patch) =>
        set((state) => {
          if (!callId) return state;
          const thread = state.aiChats[callId] ?? [];
          return {
            aiChats: {
              ...state.aiChats,
              [callId]: thread.map((msg) => {
                if (msg.id !== id) return msg;
                const nextPatch = typeof patch === 'function' ? patch(msg) : patch;
                return { ...msg, ...nextPatch };
              })
            }
          };
        }),
      resetAiMessages: (callId) =>
        set((state) => {
          if (!callId) {
            return { aiChats: {} };
          }
          const next = { ...state.aiChats };
          delete next[callId];
          return { aiChats: next };
        }),
      prompts: defaultPrompts,
      addPrompt: (prompt) =>
        set((state) => ({
          prompts: [...new Set([...state.prompts, prompt])]
        }))
    }),
    {
      name: 'call-review-ui',
      partialize: (state) => ({
        agentId: state.agentId,
        sidebarOpen: state.sidebarOpen,
        drawerOpen: state.drawerOpen,
        prompts: state.prompts
      })
    }
  )
);
