import AgentBoard from '../../../components/AgentBoard';

export const AGENT_ORDER = ['pii-scanner', 'api-auditor', 'auth-checker'];

export default function AgentStatusBoard({ agents }) {
  return <AgentBoard agents={agents} order={AGENT_ORDER} layout="stack" />;
}
