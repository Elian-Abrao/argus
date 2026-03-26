import {
  addDays,
  addMonths,
  addWeeks,
  endOfMonth,
  endOfWeek,
  format,
  isSameDay,
  isSameMonth,
  isToday,
  startOfMonth,
  startOfWeek,
  subMonths,
  subWeeks,
} from 'date-fns';
import { ptBR } from 'date-fns/locale';
import {
  Calendar,
  ChevronLeft,
  ChevronRight,
  Play,
  Plus,
  Power,
  Trash2,
} from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import FeedbackToast from '../components/FeedbackToast';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import ScheduleModal from '../components/ScheduleModal';
import SectionCard from '../components/SectionCard';
import { deleteSchedule, getCalendar, getSchedules, updateSchedule } from '../lib/api';
import { getErrorMessage } from '../lib/format';
import useHeaderRefresh from '../layout/useHeaderRefresh';

const VIEW_MODES = [
  { value: 'month', label: 'Mes' },
  { value: 'week', label: 'Semana' },
];

const RECURRENCE_LABELS = {
  daily: 'Diario',
  weekdays: 'Dias uteis',
  specific_days: 'Dias especificos',
  monthly: 'Mensal',
  yearly: 'Anual',
};

const DAY_LABELS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'];

function SchedulesPage() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [schedules, setSchedules] = useState([]);
  const [calendarEvents, setCalendarEvents] = useState([]);
  const [total, setTotal] = useState(0);

  const [viewMode, setViewMode] = useState('month');
  const [currentDate, setCurrentDate] = useState(new Date());
  const [modalOpen, setModalOpen] = useState(false);
  const [runNowOpen, setRunNowOpen] = useState(false);

  const calendarRange = useMemo(() => {
    if (viewMode === 'week') {
      const start = startOfWeek(currentDate, { locale: ptBR, weekStartsOn: 1 });
      const end = endOfWeek(currentDate, { locale: ptBR, weekStartsOn: 1 });
      return { start, end };
    }
    const monthStart = startOfMonth(currentDate);
    const monthEnd = endOfMonth(currentDate);
    const start = startOfWeek(monthStart, { locale: ptBR, weekStartsOn: 1 });
    const end = endOfWeek(monthEnd, { locale: ptBR, weekStartsOn: 1 });
    return { start, end };
  }, [currentDate, viewMode]);

  const loadData = useCallback(
    async ({ showRefreshFeedback = false } = {}) => {
      if (schedules.length > 0) setRefreshing(true);
      else setLoading(true);
      setError(null);

      try {
        const [schedulesRes, calendarRes] = await Promise.all([
          getSchedules({ limit: 200 }),
          getCalendar({
            start: calendarRange.start.toISOString(),
            end: calendarRange.end.toISOString(),
          }),
        ]);

        const items = Array.isArray(schedulesRes?.items) ? schedulesRes.items : [];
        setSchedules(items);
        setTotal(schedulesRes?.total || 0);
        setCalendarEvents(Array.isArray(calendarRes?.items) ? calendarRes.items : []);

        if (showRefreshFeedback) {
          setFeedback({ type: 'success', message: 'Agendamentos atualizados.' });
        }
      } catch (err) {
        setError(err);
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [calendarRange, schedules.length]
  );

  useEffect(() => {
    loadData();
  }, [calendarRange]);

  const navigate = (direction) => {
    setCurrentDate((prev) => {
      if (viewMode === 'week') {
        return direction === 'prev' ? subWeeks(prev, 1) : addWeeks(prev, 1);
      }
      return direction === 'prev' ? subMonths(prev, 1) : addMonths(prev, 1);
    });
  };

  const goToToday = () => setCurrentDate(new Date());

  const handleToggleEnabled = async (schedule) => {
    try {
      await updateSchedule(schedule.id, { enabled: !schedule.enabled });
      setFeedback({
        type: 'success',
        message: schedule.enabled ? 'Agendamento desabilitado.' : 'Agendamento habilitado.',
      });
      loadData();
    } catch (err) {
      setFeedback({ type: 'error', message: getErrorMessage(err) });
    }
  };

  const handleDelete = async (schedule) => {
    try {
      await deleteSchedule(schedule.id);
      setFeedback({ type: 'success', message: 'Agendamento removido.' });
      loadData();
    } catch (err) {
      setFeedback({ type: 'error', message: getErrorMessage(err) });
    }
  };

  const calendarTitle = useMemo(() => {
    if (viewMode === 'week') {
      const start = startOfWeek(currentDate, { locale: ptBR, weekStartsOn: 1 });
      const end = endOfWeek(currentDate, { locale: ptBR, weekStartsOn: 1 });
      return `${format(start, "d 'de' MMM", { locale: ptBR })} — ${format(end, "d 'de' MMM yyyy", { locale: ptBR })}`;
    }
    return format(currentDate, "MMMM 'de' yyyy", { locale: ptBR });
  }, [currentDate, viewMode]);

  const columns = useMemo(
    () => [
      {
        key: 'automation',
        header: 'Automacao',
        render: (s) => (
          <div className="whitespace-nowrap">
            <span className="font-semibold text-app-text">
              {s.automation_name || 'Automacao'}
            </span>
            {s.automation_code ? (
              <span className="ml-1.5 text-[10px] text-app-muted">#{s.automation_code}</span>
            ) : null}
          </div>
        ),
      },
      {
        key: 'client_name',
        header: 'Cliente',
        render: (s) => (
          <span className="text-app-muted">{s.client_name || 'N/D'}</span>
        ),
      },
      {
        key: 'recurrence',
        header: 'Recorrencia',
        render: (s) => (
          <span className="text-xs">{RECURRENCE_LABELS[s.recurrence_type] || s.recurrence_type}</span>
        ),
      },
      {
        key: 'time',
        header: 'Horario',
        render: (s) => (
          <span className="tabular-nums text-xs font-medium text-app-text">
            {s.recurrence_config?.time || '-'}
          </span>
        ),
      },
      {
        key: 'execution_mode',
        header: 'Modo',
        render: (s) => (
          <span
            className={`inline-flex rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider ${
              s.execution_mode === 'sequential'
                ? 'border-amber-300/60 bg-amber-100 text-amber-800'
                : 'border-sky-300/60 bg-sky-100 text-sky-800'
            }`}
          >
            {s.execution_mode === 'sequential' ? 'Sequencial' : 'Paralelo'}
          </span>
        ),
      },
      {
        key: 'enabled',
        header: 'Status',
        render: (s) => (
          <span
            className={`inline-flex rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-wider ${
              s.enabled
                ? 'border-emerald-300/60 bg-emerald-100 text-emerald-800'
                : 'border-app-border bg-app-elevated text-app-muted'
            }`}
          >
            {s.enabled ? 'Ativo' : 'Inativo'}
          </span>
        ),
      },
      {
        key: 'actions',
        header: '',
        cellClassName: 'text-right',
        render: (s) => (
          <div className="flex items-center justify-end gap-1">
            <button
              type="button"
              onClick={() => handleToggleEnabled(s)}
              title={s.enabled ? 'Desabilitar' : 'Habilitar'}
              className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-app-border text-app-muted transition hover:border-app-accent/40 hover:text-app-accent"
            >
              <Power className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => handleDelete(s)}
              title="Remover"
              className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-app-border text-app-muted transition hover:border-rose-400 hover:text-rose-500"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        ),
      },
    ],
    []
  );

  useHeaderRefresh(() => loadData({ showRefreshFeedback: true }), refreshing);

  if (loading && schedules.length === 0) {
    return <LoadingState label="Carregando agendamentos..." />;
  }

  if (error && schedules.length === 0) {
    return (
      <ErrorState
        title={error.title || 'Falha ao carregar agendamentos'}
        message={getErrorMessage(error)}
        onRetry={() => loadData()}
        busy={refreshing}
      />
    );
  }

  return (
    <>
      <PageHeader
        title="Agendamentos"
        subtitle={`${total} agendamento${total !== 1 ? 's' : ''} configurado${total !== 1 ? 's' : ''}${refreshing ? ' — Atualizando...' : ''}`}
        actions={[
          <button
            key="run-now"
            type="button"
            onClick={() => setRunNowOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl border border-app-border bg-app-surface/80 px-4 py-2 text-sm font-semibold text-app-text transition hover:bg-app-primary/10"
          >
            <Play className="h-4 w-4" /> Iniciar Agora
          </button>,
          <button
            key="new"
            type="button"
            onClick={() => setModalOpen(true)}
            className="inline-flex items-center gap-2 rounded-xl bg-[#2b114a] px-4 py-2 text-sm font-bold text-white shadow transition hover:bg-[#6d558d]"
          >
            <Plus className="h-4 w-4" /> Novo Agendamento
          </button>,
        ]}
      />

      {/* Calendar Navigation */}
      <SectionCard className="mb-6">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => navigate('prev')}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-app-border bg-app-surface text-app-muted transition hover:bg-app-primary/10"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              type="button"
              onClick={goToToday}
              className="rounded-lg border border-app-border bg-app-surface px-3 py-1 text-xs font-semibold text-app-muted transition hover:bg-app-primary/10"
            >
              Hoje
            </button>
            <button
              type="button"
              onClick={() => navigate('next')}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-app-border bg-app-surface text-app-muted transition hover:bg-app-primary/10"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
            <h3 className="ml-2 text-sm font-semibold capitalize text-app-text">{calendarTitle}</h3>
          </div>

          <div className="flex gap-1 rounded-lg border border-app-border bg-app-surface p-0.5">
            {VIEW_MODES.map((mode) => (
              <button
                key={mode.value}
                type="button"
                onClick={() => setViewMode(mode.value)}
                className={`rounded-md px-3 py-1 text-xs font-semibold transition ${
                  viewMode === mode.value
                    ? 'bg-app-accent text-white shadow-sm'
                    : 'text-app-muted hover:text-app-text'
                }`}
              >
                {mode.label}
              </button>
            ))}
          </div>
        </div>

        {/* Calendar Grid */}
        <div className="mt-4">
          {viewMode === 'month' ? (
            <MonthView
              currentDate={currentDate}
              events={calendarEvents}
              range={calendarRange}
            />
          ) : (
            <WeekView
              currentDate={currentDate}
              events={calendarEvents}
              range={calendarRange}
            />
          )}
        </div>
      </SectionCard>

      {/* Schedule List */}
      <SectionCard
        title="Todos os agendamentos"
        subtitle="Lista completa de agendamentos configurados"
      >
        {schedules.length > 0 ? (
          <div className="overflow-hidden rounded-xl border border-app-border bg-app-surface/40 shadow-sm">
            <DataTable columns={columns} rows={schedules} rowKey={(row) => row.id} />
          </div>
        ) : (
          <EmptyState
            title="Nenhum agendamento"
            message="Crie um novo agendamento para agendar execucoes de automacoes."
          />
        )}
      </SectionCard>

      {modalOpen && (
        <ScheduleModal
          mode="schedule"
          onClose={() => setModalOpen(false)}
          onCreated={() => loadData()}
        />
      )}

      {runNowOpen && (
        <ScheduleModal
          mode="run-now"
          onClose={() => setRunNowOpen(false)}
          onCreated={() => loadData()}
        />
      )}

      <FeedbackToast
        type={feedback?.type}
        message={feedback?.message}
        onDone={() => setFeedback(null)}
      />
    </>
  );
}

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

const EVENT_COLORS = [
  '#ef4444', '#f97316', '#f59e0b', '#10b981',
  '#06b6d4', '#3b82f6', '#8b5cf6', '#ec4899',
  '#14b8a6', '#84cc16',
];

function hashEventColor(name) {
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) | 0;
  return EVENT_COLORS[Math.abs(h) % EVENT_COLORS.length];
}

function evDay(ev) {
  return ev.scheduled_time ? ev.scheduled_time.slice(0, 10) : null;
}

function evHour(ev) {
  if (!ev.scheduled_time) return -1;
  const timePart = ev.scheduled_time.split('T')[1] || '';
  return parseInt(timePart.split(':')[0], 10);
}

function evTimeLabel(ev) {
  if (!ev.scheduled_time) return '';
  const timePart = ev.scheduled_time.split('T')[1] || '';
  return timePart.slice(0, 5); // HH:MM
}

function buildEventsByDay(events) {
  const map = {};
  (events || []).forEach((ev) => {
    const key = evDay(ev);
    if (!key) return;
    if (!map[key]) map[key] = [];
    map[key].push(ev);
  });
  // sort each day by scheduled_time
  Object.values(map).forEach((arr) => arr.sort((a, b) => a.scheduled_time.localeCompare(b.scheduled_time)));
  return map;
}

// ---------------------------------------------------------------------------
// Month View
// ---------------------------------------------------------------------------

function MonthView({ currentDate, events, range }) {
  const weeks = useMemo(() => {
    const rows = [];
    let day = range.start;
    while (day <= range.end) {
      const week = [];
      for (let i = 0; i < 7; i++) {
        week.push(day);
        day = addDays(day, 1);
      }
      rows.push(week);
    }
    return rows;
  }, [range]);

  const eventsByDay = useMemo(() => buildEventsByDay(events), [events]);

  return (
    <div className="overflow-hidden rounded-xl border border-app-border">
      {/* Day headers */}
      <div className="grid grid-cols-7 border-b border-app-border bg-app-elevated/60">
        {DAY_LABELS.map((label) => (
          <div key={label} className="px-2 py-2 text-center text-[10px] font-bold uppercase tracking-[0.12em] text-app-muted">
            {label}
          </div>
        ))}
      </div>

      {/* Week rows */}
      {weeks.map((week, wi) => (
        <div key={wi} className="grid grid-cols-7 divide-x divide-app-border/60 border-b border-app-border/60 last:border-b-0">
          {week.map((day) => {
            const key = format(day, 'yyyy-MM-dd');
            const dayEvents = eventsByDay[key] || [];
            const inMonth = isSameMonth(day, currentDate);
            const today = isToday(day);
            const MAX = 3;

            return (
              <div
                key={key}
                className={`min-h-[90px] p-1.5 ${inMonth ? 'bg-app-surface/30' : 'bg-app-elevated/30'}`}
              >
                <div className="mb-1 flex items-center justify-between">
                  <span className={`inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-semibold ${
                    today ? 'bg-app-accent text-white' : inMonth ? 'text-app-text' : 'text-app-muted/40'
                  }`}>
                    {format(day, 'd')}
                  </span>
                  {dayEvents.length > MAX && (
                    <span className="text-[9px] font-medium text-app-muted">+{dayEvents.length - MAX}</span>
                  )}
                </div>
                <div className="space-y-0.5">
                  {dayEvents.slice(0, MAX).map((ev, i) => (
                    <MonthEventCard key={i} event={ev} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

function MonthEventCard({ event }) {
  const [hovered, setHovered] = useState(false);
  const time = evTimeLabel(event);
  const name = event.automation_name || 'Automacao';
  const disabled = event.enabled === false;
  const color = disabled ? '#9ca3af' : hashEventColor(name);

  return (
    <div
      className="relative"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div
        style={{ backgroundColor: color }}
        className="flex cursor-default items-center gap-1 overflow-hidden rounded px-1.5 py-0.5"
      >
        <span className="shrink-0 text-[9px] font-bold tabular-nums text-white/80">{time}</span>
        <span className="truncate text-[9px] font-semibold text-white leading-tight">{name}</span>
      </div>
      {hovered && (
        <div className="absolute left-0 top-full z-50 mt-0.5 min-w-[150px] max-w-[200px] rounded-lg border border-app-border bg-app-surface p-2 shadow-2xl">
          <p className="text-[10px] font-bold text-app-text leading-tight">{name}</p>
          {event.client_name && (
            <p className="mt-0.5 text-[9px] text-app-muted">{event.client_name}</p>
          )}
          {(event.host_display_name || event.host_hostname) && (
            <p className="text-[9px] text-app-muted">{event.host_display_name || event.host_hostname}</p>
          )}
          <p className="mt-1 text-[9px] font-semibold" style={{ color }}>{time}</p>
          {disabled && <p className="mt-0.5 text-[9px] text-amber-500">Desabilitado</p>}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Week View
// ---------------------------------------------------------------------------

function WeekView({ currentDate, events, range }) {
  const days = useMemo(() => {
    const result = [];
    let day = range.start;
    for (let i = 0; i < 7; i++) {
      result.push(day);
      day = addDays(day, 1);
    }
    return result;
  }, [range]);

  const eventsByDay = useMemo(() => buildEventsByDay(events), [events]);

  // only render hours that have events or are between first/last event hour
  const hours = useMemo(() => Array.from({ length: 24 }, (_, i) => i), []);

  return (
    <div className="overflow-hidden rounded-xl border border-app-border">
      {/* Day headers */}
      <div className="grid grid-cols-[48px_repeat(7,1fr)] border-b border-app-border bg-app-elevated/60">
        <div className="border-r border-app-border/60" />
        {days.map((day) => {
          const today = isToday(day);
          return (
            <div key={format(day, 'yyyy-MM-dd')} className="border-r border-app-border/60 px-2 py-2 text-center last:border-r-0">
              <p className="text-[10px] font-bold uppercase tracking-wider text-app-muted">
                {format(day, 'EEE', { locale: ptBR })}
              </p>
              <p className={`mt-0.5 text-sm font-semibold ${today ? 'text-app-accent' : 'text-app-text'}`}>
                {format(day, 'd')}
              </p>
            </div>
          );
        })}
      </div>

      {/* Time grid */}
      <div className="max-h-[520px] overflow-y-auto custom-scrollbar">
        {hours.map((hour) => (
          <div key={hour} className="grid grid-cols-[48px_repeat(7,1fr)] border-b border-app-border/40 last:border-b-0">
            <div className="flex items-start justify-end border-r border-app-border/60 pr-2 pt-1.5 text-[10px] font-medium text-app-muted">
              {String(hour).padStart(2, '0')}:00
            </div>
            {days.map((day) => {
              const key = format(day, 'yyyy-MM-dd');
              const hourEvents = (eventsByDay[key] || []).filter((ev) => evHour(ev) === hour);
              return (
                <div key={`${key}-${hour}`} className="min-h-[40px] border-r border-app-border/30 p-0.5 last:border-r-0">
                  {hourEvents.map((ev, i) => (
                    <WeekEventCard key={i} event={ev} />
                  ))}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

function WeekEventCard({ event }) {
  const name = event.automation_name || 'Automacao';
  const client = event.client_name;
  const disabled = event.enabled === false;
  const color = disabled ? '#9ca3af' : hashEventColor(name);

  return (
    <div
      className="mb-0.5 rounded-md px-1.5 py-1"
      style={{ backgroundColor: color + '22', borderLeft: `2px solid ${color}` }}
    >
      <p className="truncate text-[9px] font-semibold" style={{ color }}>{name}</p>
      {client && <p className="truncate text-[8px] text-app-muted leading-tight">{client}</p>}
    </div>
  );
}

export default SchedulesPage;
