import { normalizeStatus } from '../lib/format';

function StatusBadge({ status, className = '' }) {
  const normalized = normalizeStatus(status);

  const style = {
    running: 'bg-amber-100 text-amber-800 border-amber-300/60',
    completed: 'bg-emerald-100 text-emerald-800 border-emerald-300/60',
    failed: 'bg-rose-100 text-rose-800 border-rose-300/60',
    stopped: 'bg-orange-100 text-orange-700 border-orange-300/60',
    unknown: 'bg-app-elevated text-app-muted border-app-border',
  }[normalized];

  return (
    <span
      className={`inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-[0.08em] ${style} ${className}`}
    >
      {status || 'indefinido'}
    </span>
  );
}

export default StatusBadge;
