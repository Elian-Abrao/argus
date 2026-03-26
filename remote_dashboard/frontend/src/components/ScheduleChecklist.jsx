import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react';
import { formatTime, normalizeStatus } from '../lib/format';

const WEEKDAY_FMT = new Intl.DateTimeFormat('pt-BR', { weekday: 'short' });
const DATE_FMT = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit' });

// Janela de tolerância para fallback via timeline (2 horas)
const FALLBACK_WINDOW_MS = 2 * 60 * 60 * 1000;

function formatDayTime(value) {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  const weekday = WEEKDAY_FMT.format(d).replace('.', '');
  return `${weekday} ${formatTime(d)}`;
}

function formatDate(value) {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return DATE_FMT.format(d);
}

function getLocalDayStartMs(value) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return Number.NaN;
  d.setHours(0, 0, 0, 0);
  return d.getTime();
}

function getMidpointMs(leftMs, rightMs) {
  return leftMs + Math.floor((rightMs - leftMs) / 2);
}

/**
 * Cruza CalendarEvents com Commands (via scheduled_job_id).
 * Fallback: busca na timeline por automation_instance_id + proximidade de horário.
 * Filtra eventos futuros (dias além de hoje são omitidos; hora futura hoje = "Aguardando").
 */
function buildChecklist(calendarItems, commandItems, timelineItems) {
  const now = new Date();
  const nowMs = now.getTime();
  const todayStartMs = getLocalDayStartMs(now);
  const sortedEvents = [...calendarItems]
    .filter((event) => !Number.isNaN(new Date(event.scheduled_time).getTime()))
    .sort((left, right) => (
      new Date(left.scheduled_time).getTime() - new Date(right.scheduled_time).getTime()
    ));

  // Indexa commands por scheduled_job_id
  const byJobId = new Map();
  for (const cmd of commandItems) {
    if (!cmd.scheduled_job_id) continue;
    const key = String(cmd.scheduled_job_id);
    if (!byJobId.has(key)) byJobId.set(key, []);
    byJobId.get(key).push(cmd);
  }

  // Indexa timeline runs por automation_instance_id para fallback
  const runsByInstance = new Map();
  for (const run of timelineItems) {
    if (!run.automation_instance_id) continue;
    const key = String(run.automation_instance_id);
    if (!runsByInstance.has(key)) runsByInstance.set(key, []);
    runsByInstance.get(key).push(run);
  }

  // Calcula a janela de cada ocorrencia para nao reutilizar a execucao
  // de um dia em outra ocorrencia futura do mesmo agendamento recorrente.
  const eventWindows = new Map();
  const eventsByJobId = new Map();
  for (const event of sortedEvents) {
    const key = String(event.id);
    if (!eventsByJobId.has(key)) eventsByJobId.set(key, []);
    eventsByJobId.get(key).push(event);
  }

  eventsByJobId.forEach((events) => {
    events.forEach((event, index) => {
      const scheduledMs = new Date(event.scheduled_time).getTime();
      const previous = index > 0 ? events[index - 1] : null;
      const next = index < events.length - 1 ? events[index + 1] : null;

      const previousMs = previous ? new Date(previous.scheduled_time).getTime() : null;
      const nextMs = next ? new Date(next.scheduled_time).getTime() : null;

      const windowStartMs = previousMs != null
        ? getMidpointMs(previousMs, scheduledMs)
        : Number.NEGATIVE_INFINITY;
      const windowEndMs = nextMs != null
        ? getMidpointMs(scheduledMs, nextMs)
        : Number.POSITIVE_INFINITY;

      eventWindows.set(`${event.id}-${event.scheduled_time}`, { windowStartMs, windowEndMs });
    });
  });

  const result = [];

  for (const event of sortedEvents) {
    const scheduledMs = new Date(event.scheduled_time).getTime();
    const eventDayStartMs = getLocalDayStartMs(event.scheduled_time);
    const eventWindow = eventWindows.get(`${event.id}-${event.scheduled_time}`);
    const windowStartMs = eventWindow?.windowStartMs ?? Number.NEGATIVE_INFINITY;
    const windowEndMs = eventWindow?.windowEndMs ?? Number.POSITIVE_INFINITY;

    // Omite dias futuros (além de hoje)
    if (Number.isNaN(scheduledMs) || Number.isNaN(eventDayStartMs)) continue;

    // Tenta match por scheduled_job_id
    const jobKey = String(event.id);
    const candidates = (byJobId.get(jobKey) || []).filter((cmd) => {
      const createdAtMs = new Date(cmd.created_at).getTime();
      return createdAtMs >= windowStartMs && createdAtMs < windowEndMs;
    });
    let cmd = candidates.length
      ? candidates.reduce((best, c) => {
          const bestDiff = Math.abs(new Date(best.created_at).getTime() - scheduledMs);
          const cDiff = Math.abs(new Date(c.created_at).getTime() - scheduledMs);
          return cDiff < bestDiff ? c : best;
        })
      : null;

    // Fallback: busca run na timeline com mesmo automation_instance_id e horário próximo
    let fallbackRun = null;
    if (!cmd) {
      const instanceRuns = runsByInstance.get(String(event.automation_instance_id)) || [];
      const close = instanceRuns.filter((run) => {
        const runMs = new Date(run.started_at).getTime();
        return (
          runMs >= windowStartMs &&
          runMs < windowEndMs &&
          Math.abs(runMs - scheduledMs) <= FALLBACK_WINDOW_MS
        );
      });
      if (close.length) {
        // Pega o mais próximo do horário agendado
        fallbackRun = close.reduce((best, r) => {
          const bd = Math.abs(new Date(best.started_at).getTime() - scheduledMs);
          const rd = Math.abs(new Date(r.started_at).getTime() - scheduledMs);
          return rd < bd ? r : best;
        });
      }
    }

    const hasExecutionEvidence = cmd != null || fallbackRun != null;

    // Se ja houve comando/run associado, nao tratamos mais como "futuro",
    // mesmo que haja alguma diferenca de timezone ou o processo tenha virado a meia-noite.
    const isFuture = !hasExecutionEvidence && (
      eventDayStartMs > todayStartMs ||
      (eventDayStartMs === todayStartMs && scheduledMs > nowMs)
    );

    // Omite dias futuros (além de hoje) quando realmente ainda nao ha sinal de execucao.
    if (eventDayStartMs > todayStartMs && !hasExecutionEvidence) continue;

    const initiated = isFuture ? false : (cmd != null || fallbackRun != null);
    const executed = !isFuture && (
      (cmd != null && (cmd.run_id != null || cmd.finished_at != null || cmd.status === 'completed')) ||
      (fallbackRun != null && !!fallbackRun.finished_at)
    );
    const isRunning = !isFuture && (
      cmd?.status === 'running' || cmd?.status === 'acked' ||
      (fallbackRun != null && normalizeStatus(fallbackRun.status) === 'running')
    );
    const isFailed = !isFuture && initiated && !isRunning && (
      cmd?.status === 'failed' || cmd?.status === 'cancelled' ||
      (fallbackRun != null && normalizeStatus(fallbackRun.status) === 'failed')
    );

    result.push({
      event,
      cmd,
      fallbackRun,
      initiated,
      executed,
      isRunning,
      isFailed,
      isFuture,
    });
  }

  return result;
}

function StatusDot({ initiated, executed, isRunning, isFailed, isFuture }) {
  if (isFuture) return <Clock className="h-4 w-4 text-sky-400 shrink-0" />;
  if (!initiated) return <XCircle className="h-4 w-4 text-rose-400 shrink-0" />;
  if (isRunning) return <Loader2 className="h-4 w-4 text-amber-500 animate-spin shrink-0" />;
  if (isFailed) return <XCircle className="h-4 w-4 text-rose-500 shrink-0" />;
  if (executed) return <CheckCircle2 className="h-4 w-4 text-emerald-500 shrink-0" />;
  return <Clock className="h-4 w-4 text-app-muted shrink-0" />;
}

function CheckMark({ ok, time, running, future }) {
  if (future) {
    return <span className="text-[11px] text-sky-500 font-medium">Aguardando</span>;
  }
  if (running) {
    return (
      <span className="flex items-center gap-1 text-amber-600">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span className="font-mono text-[11px]">{time || '—'}</span>
      </span>
    );
  }
  if (ok) {
    return (
      <span className="flex items-center gap-1 text-emerald-600">
        <CheckCircle2 className="h-3 w-3" />
        <span className="font-mono text-[11px]">{time || '—'}</span>
      </span>
    );
  }
  return (
    <span className="flex items-center gap-1 text-rose-400">
      <XCircle className="h-3 w-3" />
      <span className="text-[11px] text-app-muted">—</span>
    </span>
  );
}

function ScheduleChecklist({ calendarItems = [], commandItems = [], timelineItems = [] }) {
  const checklist = useMemo(
    () => buildChecklist(calendarItems, commandItems, timelineItems),
    [calendarItems, commandItems, timelineItems]
  );

  if (!checklist.length) return null;

  const colCls = {
    status: 'w-6 shrink-0 flex items-center justify-center',
    name:   'flex min-w-0 flex-1 items-center gap-2',
    sched:  'hidden w-32 shrink-0 md:block',
    init:   'hidden w-32 shrink-0 sm:block',
    exec:   'hidden w-32 shrink-0 sm:block',
    badge:  'w-24 shrink-0 flex justify-end',
  };

  const badgeStyles = {
    completed: 'text-emerald-700 bg-emerald-50 border-emerald-200',
    running:   'text-amber-700 bg-amber-50 border-amber-200',
    failed:    'text-rose-700 bg-rose-50 border-rose-200',
    pending:   'text-app-muted bg-app-surface border-app-border',
    missed:    'text-rose-600 bg-rose-50 border-rose-200',
    waiting:   'text-sky-600 bg-sky-50 border-sky-200',
  };

  function getBadgeTone(item) {
    if (item.isFuture) return 'waiting';
    if (!item.initiated) return 'missed';
    if (item.isRunning) return 'running';
    if (item.isFailed) return 'failed';
    if (item.executed) return 'completed';
    return 'pending';
  }

  function getBadgeLabel(item) {
    if (item.isFuture) return 'Aguardando';
    if (!item.initiated) return 'Nao disparado';
    if (item.isRunning) return 'Executando';
    if (item.isFailed) return 'Falha';
    if (item.executed) return 'Concluido';
    return 'Pendente';
  }

  let lastDate = null;

  return (
    <div className="divide-y divide-app-border/40 -mx-4 -mb-4 overflow-hidden rounded-b-2xl">
      {/* Header */}
      <div className="hidden items-center gap-4 bg-app-elevated/60 px-4 py-2 md:flex">
        <span className={colCls.status} />
        <span className={`${colCls.name} text-[10px] font-bold uppercase tracking-[0.12em] text-app-muted`}>Robo / Cliente</span>
        <span className={`${colCls.sched} text-[10px] font-bold uppercase tracking-[0.12em] text-app-muted`}>Previsto</span>
        <span className={`${colCls.init} text-[10px] font-bold uppercase tracking-[0.12em] text-app-muted`}>Iniciado</span>
        <span className={`${colCls.exec} text-[10px] font-bold uppercase tracking-[0.12em] text-app-muted`}>Executado</span>
        <span className={`${colCls.badge} text-[10px] font-bold uppercase tracking-[0.12em] text-app-muted`}>Status</span>
      </div>

      {checklist.map((item, idx) => {
        const { event, cmd, fallbackRun } = item;
        const scheduledDate = formatDate(event.scheduled_time);
        const showDateSep = scheduledDate !== lastDate;
        lastDate = scheduledDate;

        const robotLabel = event.automation_name || event.automation_code || 'Robo sem nome';
        const tone = getBadgeTone(item);

        // Horário de início: command tem prioridade, fallback usa a run da timeline
        const initiatedTime = cmd?.started_at
          ? formatDayTime(cmd.started_at)
          : cmd?.acked_at
            ? formatDayTime(cmd.acked_at)
            : cmd?.created_at
              ? formatDayTime(cmd.created_at)
              : fallbackRun?.started_at
                ? formatDayTime(fallbackRun.started_at)
                : null;

        const executedTime = cmd?.finished_at
          ? formatDayTime(cmd.finished_at)
          : fallbackRun?.finished_at
            ? formatDayTime(fallbackRun.finished_at)
            : null;

        // Link para a run (command tem prioridade, depois fallback)
        const runId = cmd?.run_id || fallbackRun?.id || null;

        const rowContent = (
          <div className={`group flex items-center gap-4 px-4 py-2.5 transition w-full ${item.isFuture ? 'opacity-50' : 'hover:bg-app-elevated/60'}`}>
            <div className={colCls.status}>
              <StatusDot
                initiated={item.initiated}
                executed={item.executed}
                isRunning={item.isRunning}
                isFailed={item.isFailed}
                isFuture={item.isFuture}
              />
            </div>

            <div className={colCls.name}>
              <div className="min-w-0">
                {runId && !item.isFuture ? (
                  <span className="block truncate text-sm font-semibold text-app-accent underline underline-offset-2 decoration-app-accent/40">
                    {robotLabel}
                  </span>
                ) : event.automation_id ? (
                  <Link
                    to={`/automations/${event.automation_id}/runs`}
                    onClick={(e) => e.stopPropagation()}
                    className="block truncate text-sm font-semibold text-app-accent hover:underline"
                  >
                    {robotLabel}
                  </Link>
                ) : (
                  <span className="block truncate text-sm font-semibold text-app-text">
                    {robotLabel}
                  </span>
                )}
                {event.client_name ? (
                  (!runId || item.isFuture) && event.client_id ? (
                    <Link
                      to={`/clients/${event.client_id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="block truncate text-[11px] text-app-muted hover:text-app-accent hover:underline"
                    >
                      {event.client_name}
                    </Link>
                  ) : (
                    <span className="block truncate text-[11px] text-app-muted">{event.client_name}</span>
                  )
                ) : null}
              </div>
            </div>

            <span className={`${colCls.sched} font-mono text-[11px] text-app-muted whitespace-nowrap`}>
              {formatDayTime(event.scheduled_time) || '—'}
            </span>

            <div className={colCls.init}>
              <CheckMark
                ok={item.initiated}
                time={initiatedTime}
                running={item.isRunning && !!cmd?.started_at}
                future={item.isFuture}
              />
            </div>

            <div className={colCls.exec}>
              <CheckMark
                ok={item.executed && !item.isRunning}
                time={executedTime}
                running={false}
                future={item.isFuture}
              />
            </div>

            <div className={colCls.badge}>
              <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-bold uppercase tracking-[0.1em] ${badgeStyles[tone]}`}>
                {getBadgeLabel(item)}
              </span>
            </div>
          </div>
        );

        return (
          <div key={`${event.id}-${event.scheduled_time}-${idx}`}>
            {showDateSep && (
              <div className="flex items-center gap-2 bg-app-elevated/40 px-4 py-1.5">
                <span className="text-[10px] font-bold uppercase tracking-widest text-app-accent">
                  {scheduledDate}
                </span>
                <span className="flex-1 border-t border-app-border/40" />
              </div>
            )}
            {runId && !item.isFuture ? (
              <Link to={`/runs/${runId}`} className="block">
                {rowContent}
              </Link>
            ) : (
              <div>{rowContent}</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default ScheduleChecklist;
