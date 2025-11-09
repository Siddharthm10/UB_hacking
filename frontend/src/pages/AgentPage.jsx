import { useParams } from 'react-router-dom';
import { DashboardPage } from './DashboardPage';

export default function AgentPage() {
  const { agentId } = useParams();
  return <DashboardPage agentId={agentId} />;
}
