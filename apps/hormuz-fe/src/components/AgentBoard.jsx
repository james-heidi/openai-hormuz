import AgentCard from './AgentCard';

export default function AgentBoard({ agents, order, layout = 'grid' }) {
  const list = Array.isArray(agents) ? agents : Object.values(agents ?? {});
  const sorted = order && order.length
    ? [
        ...order
          .map((id) => list.find((a) => a.id === id))
          .filter(Boolean),
        ...list.filter((a) => !order.includes(a.id)),
      ]
    : list;

  if (sorted.length === 0) {
    return (
      <div className="glass-subpanel theme-transition rounded-lg border-dashed p-6 text-center text-sm text-text-dim shadow-none">
        Agents will appear here once a run starts.
      </div>
    );
  }

  return (
    <div className={layout === 'stack' ? 'grid grid-cols-1 gap-3' : 'grid grid-cols-1 gap-3 md:grid-cols-3'}>
      {sorted.map((a) => (
        <AgentCard key={a.id} agent={a} />
      ))}
    </div>
  );
}
