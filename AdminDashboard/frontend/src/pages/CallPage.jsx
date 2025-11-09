import { useParams } from 'react-router-dom';
import { DashboardPage } from './DashboardPage';

export default function CallPage() {
  const { agentId, callId } = useParams();
  return <DashboardPage agentId={agentId} callIdFromRoute={callId} />;
}
