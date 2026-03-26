import {
  Activity,
  AlertTriangle,
  Bot,
  Building2,
  ChartNoAxesColumn,
  List,
  Clock3,
  HardDrive,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import {
  Area,
  AreaChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import ExecutionTimeline from '../components/ExecutionTimeline';
import ExecutionTimelineList from '../components/ExecutionTimelineList';
import ScheduleChecklist from '../components/ScheduleChecklist';
import FeedbackToast from '../components/FeedbackToast';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import { getDashboardOverviewData } from '../lib/api';
import {
  formatDuration,
  getErrorMessage,
  normalizeStatus,
  toNumber,
} from '../lib/format';
import useHeaderRefresh from '../layout/useHeaderRefresh';

const statusColors = {
  running: '#ffbf4d',
  completed: '#27d69b',
  failed: '#ff6f91',
  unknown: '#94a7c9',
};

const statusLabels = {
  running: 'Em execucao',
  completed: 'Concluidos',
  failed: 'Falhas',
  unknown: 'Outros',
};

function MetricChip({ icon: Icon, label, value, tone = 'neutral', iconClass = '' }) {
  const base = 'flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors';
  const tones = {
    neutral: 'text-app-muted bg-white border-app-border',
    primary: 'text-app-accent bg-app-primary/8 border-app-primary/25',
    warning: value > 0
      ? 'text-amber-700 bg-amber-50 border-amber-200'
      : 'text-app-muted bg-white border-app-border',
    danger: value > 0
      ? 'text-rose-700 bg-rose-50 border-rose-200'
      : 'text-app-muted bg-white border-app-border',
  };

  return (
    <div className={`${base} ${tones[tone]}`}>
      <Icon className={`h-3 w-3 shrink-0 ${iconClass}`} />
      <span className="text-[11px] tracking-wide">{label}</span>
      <span className="font-bold">{value}</span>
    </div>
  );
}

function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [timelineViewMode, setTimelineViewMode] = useState('timeline');

  const loadData = async ({ showRefreshFeedback = false } = {}) => {
    if (data) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError(null);
    try {
      const payload = await getDashboardOverviewData();
      setData(payload);
      if (showRefreshFeedback) {
        setFeedback({ type: 'success', message: 'Painel atualizado com sucesso.' });
      }
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  useHeaderRefresh(() => loadData({ showRefreshFeedback: true }), refreshing);

  const timelineItems = useMemo(() => {
    const base = data?.timeline?.items || [];
    return base.map((item) => decorateTimelineItem(item));
  }, [data]);

  const calendarItems = useMemo(() => data?.calendar?.items || [], [data]);
  const commandItems = useMemo(() => data?.commands?.items || [], [data]);

  const stats = useMemo(() => {
    const statusSummary = { running: 0, completed: 0, failed: 0, unknown: 0 };
    timelineItems.forEach((item) => {
      statusSummary[item.normalizedStatus] += 1;
    });
    return {
      hosts: toNumber(data?.hosts?.total),
      automations: toNumber(data?.automations?.total),
      clients: toNumber(data?.clients?.total),
      runsToday: timelineItems.length,
      running: statusSummary.running,
      failed: statusSummary.failed,
      statusSummary,
    };
  }, [data, timelineItems]);

  const statusChartData = useMemo(
    () =>
      [
        { name: statusLabels.running, key: 'running', value: stats.statusSummary.running },
        { name: statusLabels.completed, key: 'completed', value: stats.statusSummary.completed },
        { name: statusLabels.failed, key: 'failed', value: stats.statusSummary.failed },
        { name: statusLabels.unknown, key: 'unknown', value: stats.statusSummary.unknown },
      ].filter((item) => item.value > 0),
    [stats]
  );

  const hourlyChartData = useMemo(() => {
    const { startMs, endMs } = getLastBusinessDayLocalBoundsMs();
    const bucket = new Map();

    timelineItems.forEach((item) => {
      const date = new Date(item.started_at);
      if (Number.isNaN(date.getTime())) return;
      const startedAtMs = date.getTime();
      if (startedAtMs < startMs || startedAtMs > endMs) return;
      const hour = date.getHours();
      bucket.set(hour, (bucket.get(hour) || 0) + 1);
    });

    return [...bucket.entries()]
      .sort((left, right) => left[0] - right[0])
      .map(([hour, total]) => ({ hour: `${String(hour).padStart(2, '0')}h`, total }));
  }, [timelineItems]);

  const metricsStrip = (
    <div className="flex flex-wrap items-center gap-2">
      <MetricChip icon={HardDrive} label="Maquinas" value={stats.hosts} tone="neutral" iconClass="text-violet-400" />
      <MetricChip icon={Bot} label="Robos" value={stats.automations} tone="neutral" iconClass="text-emerald-500" />
      <MetricChip icon={Building2} label="Clientes" value={stats.clients} tone="neutral" iconClass="text-sky-500" />
      <span className="mx-1 h-4 w-px bg-app-border/60" aria-hidden="true" />
      <MetricChip icon={Activity} label="Runs hoje" value={stats.runsToday} tone="primary" iconClass="text-app-accent" />
      <MetricChip icon={Clock3} label="Executando" value={stats.running} tone="warning" iconClass={stats.running > 0 ? 'text-amber-500' : 'text-app-muted'} />
      <MetricChip icon={AlertTriangle} label="Falhas" value={stats.failed} tone="danger" iconClass={stats.failed > 0 ? 'text-rose-500' : 'text-app-muted'} />
    </div>
  );

  const timelineCardSubtitle =
    timelineViewMode === 'timeline'
      ? 'Escala temporal com empilhamento automatico para concorrencias'
      : 'Lista por ordem de termino; execucoes em andamento ficam no topo';

  const timelineToggleLabel =
    timelineViewMode === 'timeline' ? 'Trocar para lista' : 'Trocar para timeline';

  if (loading && !data) {
    return <LoadingState label="Carregando visao geral operacional..." />;
  }

  if (error && !data) {
    return (
      <ErrorState
        title={error.title || 'Falha na visao geral'}
        message={getErrorMessage(error)}
        busy={refreshing}
        onRetry={() => loadData()}
      />
    );
  }

  return (
    <>
      <PageHeader
        title="Visao geral"
        subtitle={refreshing ? 'Atualizando...' : 'Execucoes e automacoes em tempo real.'}
        extra={metricsStrip}
      />

      {error ? (
        <div className="mb-4">
          <ErrorState
            title={error.title || 'Falha parcial'}
            message={getErrorMessage(error)}
            busy={refreshing}
            onRetry={() => loadData({ showRefreshFeedback: true })}
          />
        </div>
      ) : null}

      {/* Charts */}
      <section className="mb-6 grid gap-4 xl:grid-cols-12">
        {/* Donut — distribuicao por status */}
        <SectionCard
          title="Status de hoje"
          subtitle="Distribuicao por resultado"
          className="xl:col-span-4"
        >
          {statusChartData.length ? (
            <div className="h-44 pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={statusChartData}
                    dataKey="value"
                    nameKey="name"
                    innerRadius={52}
                    outerRadius={78}
                    strokeWidth={0}
                  >
                    {statusChartData.map((item) => (
                      <Cell key={item.key} fill={statusColors[item.key]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: '#ffffff',
                      borderColor: 'rgba(130,10,209,0.15)',
                      borderRadius: '10px',
                      color: '#2b114a',
                      fontSize: '12px',
                      padding: '6px 10px',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="Sem status para hoje" message="Nao ha execucoes suficientes para o grafico." />
          )}
        </SectionCard>

        {/* Area chart — volume por horario */}
        <SectionCard
          title="Volume por horario"
          subtitle="Inicio de execucoes ao longo do dia"
          className="xl:col-span-8"
        >
          {hourlyChartData.length ? (
            <div className="h-44 pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={hourlyChartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                  <defs>
                    <linearGradient id="volumeGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#820ad1" stopOpacity={0.18} />
                      <stop offset="100%" stopColor="#820ad1" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <XAxis
                    dataKey="hour"
                    stroke="#6d558d"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 11, fill: '#6d558d' }}
                  />
                  <YAxis
                    stroke="#6d558d"
                    axisLine={false}
                    tickLine={false}
                    tick={{ fontSize: 11, fill: '#6d558d' }}
                    width={24}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: '#ffffff',
                      borderColor: 'rgba(130,10,209,0.15)',
                      borderRadius: '10px',
                      color: '#2b114a',
                      fontSize: '12px',
                      padding: '6px 10px',
                    }}
                    cursor={{ stroke: 'rgba(130,10,209,0.15)', strokeWidth: 1 }}
                  />
                  <Area
                    type="monotone"
                    dataKey="total"
                    stroke="#820ad1"
                    strokeWidth={2.5}
                    fill="url(#volumeGradient)"
                    dot={{ r: 3.5, fill: '#f0e6ff', stroke: '#820ad1', strokeWidth: 2 }}
                    activeDot={{ r: 5, fill: '#820ad1', stroke: '#f0e6ff', strokeWidth: 2 }}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyState title="Sem dados por horario" message="Nao ha execucoes para montar distribuicao." />
          )}
        </SectionCard>
      </section>

      {/* Timeline */}
      <SectionCard
        title="Execucoes de hoje"
        subtitle={timelineCardSubtitle}
        actions={(
          <button
            type="button"
            onClick={() => setTimelineViewMode((current) => (current === 'timeline' ? 'list' : 'timeline'))}
            className={`flex h-9 w-9 items-center justify-center rounded-xl border transition hover:border-app-accent/40 hover:text-app-text ${
              timelineViewMode === 'list'
                ? 'border-app-accent bg-app-accent text-white shadow-sm hover:bg-app-accent/90'
                : 'border-app-border bg-app-primary/5 text-app-muted hover:bg-app-primary/15'
            }`}
            title={timelineToggleLabel}
            aria-label={timelineToggleLabel}
            aria-pressed={timelineViewMode === 'list'}
          >
            {timelineViewMode === 'timeline' ? (
              <ChartNoAxesColumn className="h-4 w-4" />
            ) : (
              <List className="h-4 w-4" />
            )}
          </button>
        )}
      >
        {timelineItems.length ? (
          timelineViewMode === 'timeline' ? (
            <ExecutionTimeline items={timelineItems} />
          ) : (
            <ExecutionTimelineList items={timelineItems} />
          )
        ) : (
          <EmptyState title="Sem execucoes hoje" message="Nao houve runs no periodo selecionado." />
        )}
      </SectionCard>

      {/* Checklist de agendamentos */}
      {calendarItems.length > 0 && (
        <SectionCard
          title="Checklist de agendamentos"
          subtitle="Agendamentos previstos no periodo e status de execucao"
          className="mt-6"
        >
          <ScheduleChecklist calendarItems={calendarItems} commandItems={commandItems} timelineItems={timelineItems} />
        </SectionCard>
      )}

      <FeedbackToast
        type={feedback?.type}
        message={feedback?.message}
        onClose={() => setFeedback(null)}
      />
    </>
  );
}

function decorateTimelineItem(item) {
  const now = new Date();
  const startedAt = item.started_at ? new Date(item.started_at) : null;
  const finishedAt = item.finished_at ? new Date(item.finished_at) : null;
  const lastLogAt = item.last_log_at ? new Date(item.last_log_at) : null;

  const noLogsForLong =
    !finishedAt && lastLogAt && now.getTime() - lastLogAt.getTime() > 15 * 60 * 1000;

  const overlap = !finishedAt && (Boolean(item.has_overlap) || Boolean(item.has_code_overlap));

  return {
    ...item,
    normalizedStatus: normalizeStatus(item.status),
    displayStatus: noLogsForLong ? 'stopped' : item.status || 'indefinido',
    durationLabel: formatDuration(startedAt, finishedAt),
    alertTone: noLogsForLong ? 'warning' : overlap ? 'critical' : null,
    alertLabel: noLogsForLong
      ? 'Sem logs ha mais de 15 minutos.'
      : overlap
        ? 'Execucao concorrente detectada.'
        : null,
  };
}

function getLastBusinessDayLocalBoundsMs() {
  const now = new Date();
  const day = now.getDay(); // 0=Dom, 1=Seg, ..., 6=Sab
  const daysBack = day === 1 ? 3 : day === 0 ? 2 : 1;

  const start = new Date(now);
  start.setDate(start.getDate() - daysBack);
  start.setHours(0, 0, 0, 0);

  const end = new Date(now);
  end.setHours(23, 59, 59, 999);
  return { startMs: start.getTime(), endMs: end.getTime() };
}

export default DashboardPage;
