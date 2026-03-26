import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { formatTime, formatDuration } from '../lib/format';

const WEEKDAY_FMT = new Intl.DateTimeFormat('pt-BR', { weekday: 'short' });

function formatDayTime(date) {
  if (!date) return null;
  const weekday = WEEKDAY_FMT.format(date).replace('.', '');
  return `${weekday} ${formatTime(date)}`;
}

function isSameDay(a, b) {
  if (!a || !b) return false;
  return a.getFullYear() === b.getFullYear()
    && a.getMonth() === b.getMonth()
    && a.getDate() === b.getDate();
}

function toDate(value) {
  if (!value) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function getOrderingMs(run) {
  if (run.finishedAt) return run.finishedAt.getTime();
  if (run.lastLogAt) return run.lastLogAt.getTime();
  return run.startedAt.getTime();
}

function buildRuns(items) {
  return items
    .map((item) => {
      const startedAt = toDate(item.started_at);
      if (!startedAt) return null;
      return {
        ...item,
        startedAt,
        finishedAt: toDate(item.finished_at),
        lastLogAt: toDate(item.last_log_at),
      };
    })
    .filter(Boolean)
    .sort((left, right) => {
      const leftMs = left.finishedAt ? left.finishedAt.getTime() : Number.POSITIVE_INFINITY;
      const rightMs = right.finishedAt ? right.finishedAt.getTime() : Number.POSITIVE_INFINITY;
      if (leftMs !== rightMs) return rightMs - leftMs;
      return getOrderingMs(right) - getOrderingMs(left);
    })
    .map((run) => {
      const isRunning = !run.finishedAt;
      const isFailed = run.normalizedStatus === 'failed' || run.alertTone === 'critical';
      return {
        ...run,
        robotLabel: run.automation_name || run.automation_code || 'Robo sem nome',
        isRunning,
        isFailed,
      };
    });
}

const dotStyles = {
  running: 'bg-amber-400',
  failed: 'bg-rose-500',
  completed: 'bg-emerald-500',
};

const badgeStyles = {
  running: 'text-amber-700 bg-amber-50 border-amber-200',
  failed: 'text-rose-700 bg-rose-50 border-rose-200',
  completed: 'text-emerald-700 bg-emerald-50 border-emerald-200',
};

function ExecutionTimelineList({ items = [] }) {
  const runs = useMemo(() => buildRuns(items), [items]);

  if (!runs.length) return null;

  const colCls = {
    name: 'flex min-w-0 flex-1 items-center gap-2.5',
    host: 'hidden w-36 shrink-0 lg:block',
    time: 'hidden w-56 shrink-0 md:block',
    dur:  'hidden w-16 shrink-0 md:block',
    badge:'w-20 shrink-0 flex justify-end',
  };

  return (
    <div className="divide-y divide-app-border/40 -mx-4 -mb-4 overflow-hidden rounded-b-2xl">
      {/* Header */}
      <div className="hidden items-center gap-4 bg-app-elevated/60 px-4 py-2 md:flex">
        <span className={`${colCls.name} text-[10px] font-bold uppercase tracking-[0.12em] text-app-muted`}>Robo / Cliente</span>
        <span className={`${colCls.host} text-[10px] font-bold uppercase tracking-[0.12em] text-app-muted`}>Host</span>
        <span className={`${colCls.time} text-[10px] font-bold uppercase tracking-[0.12em] text-app-muted`}>Horario</span>
        <span className={`${colCls.dur}  text-[10px] font-bold uppercase tracking-[0.12em] text-app-muted`}>Duracao</span>
        <span className={`${colCls.badge} text-[10px] font-bold uppercase tracking-[0.12em] text-app-muted`}>Status</span>
      </div>

      {runs.map((run) => {
        const tone = run.isRunning ? 'running' : run.isFailed ? 'failed' : 'completed';
        const startLabel = formatDayTime(run.startedAt);
        const endLabel = run.finishedAt
          ? (isSameDay(run.startedAt, run.finishedAt)
              ? formatTime(run.finishedAt)
              : formatDayTime(run.finishedAt))
          : null;
        const timeLabel = endLabel
          ? `${startLabel} → ${endLabel}`
          : `${startLabel} →`;

        return (
          <Link
            key={run.id}
            to={`/runs/${run.id}`}
            className="group flex items-center gap-4 px-4 py-2.5 transition hover:bg-app-elevated/60"
          >
            {/* Robo + cliente */}
            <div className={colCls.name}>
              <span className={`h-2 w-2 shrink-0 rounded-full ${dotStyles[tone]} ${run.isRunning ? 'animate-pulse' : ''}`} />
              <div className="min-w-0">
                <span className="block truncate text-sm font-semibold text-app-text group-hover:text-app-accent transition-colors">
                  {run.robotLabel}
                </span>
                {run.client_name ? (
                  <span className="block truncate text-[11px] text-app-muted">{run.client_name}</span>
                ) : null}
              </div>
            </div>

            {/* Host */}
            <span className={`${colCls.host} truncate text-xs text-app-muted`}>
              {run.host_display_name || run.host_hostname || '—'}
            </span>

            {/* Horario */}
            <span className={`${colCls.time} font-mono text-[11px] text-app-muted whitespace-nowrap`}>
              {timeLabel}
            </span>

            {/* Duracao */}
            <span className={`${colCls.dur} text-xs text-app-muted`}>
              {formatDuration(run.startedAt, run.finishedAt)}
            </span>

            {/* Status badge */}
            <div className={colCls.badge}>
              <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.1em] ${badgeStyles[tone]}`}>
                {run.isRunning ? 'Executando' : ['stopped', 'cancelled'].includes(run.status) ? 'Parado' : run.isFailed ? 'Falha' : 'Concluido'}
              </span>
            </div>
          </Link>
        );
      })}
    </div>
  );
}

export default ExecutionTimelineList;
