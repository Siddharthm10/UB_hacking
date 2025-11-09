import { Navigate, Route, Routes } from 'react-router-dom';
import { ChatShell } from '@/components/layout/ChatShell';
import LandingPage from '@/pages/LandingPage';
import AgentPage from '@/pages/AgentPage';
import CallPage from '@/pages/CallPage';

export default function App() {
  return (
    <ChatShell>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/a/:agentId" element={<AgentPage />} />
        <Route path="/a/:agentId/c/:callId" element={<CallPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </ChatShell>
  );
}
