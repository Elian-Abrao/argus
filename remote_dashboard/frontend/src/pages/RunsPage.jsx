import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Clock3,
  FileText,
  MousePointerClick,
  RefreshCw,
  Search,
  SortAsc,
  SortDesc,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import BusyButton from '../components/BusyButton';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import FeedbackToast from '../components/FeedbackToast';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import StatusBadge from '../components/StatusBadge';
import {
  getAutomationDetail,
  getAutomationRuns,
  getClients,
  getHosts,
  getInstanceRuns,
  getRuns,
  getRunsOverview,
} from '../lib/api';
import {
  formatDateTime,
  formatDuration,
  formatTime,
  getErrorMessage,
  normalizeStatus,
} from '../lib/format';
import useHeaderRefresh from '../layout/useHeaderRefresh';

const ITEMS_PER_PAGE = 20;

const statusColors = {
  running: '#ffbf4d',
  completed: '#27d69b',
  failed: '#ff6f91',
  stopped: '#fb923c',
  unknown: '#94a7c9',
};

function RunsPage() {
  const { automationId, instanceId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [feedback, setFeedback] = useState(null);

  const isGlobal = !automationId && !instanceId;
  const isAutomation = Boolean(automationId);
  const sortField = searchParams.get('sort_by') || 'started_at';
  const sortOrder = searchParams.get('order') || 'desc';
  const currentPageParam = Number.parseInt(searchParams.get('page') || '1', 10);
  const currentPage = Number.isFinite(currentPageParam) && currentPageParam > 0 ? currentPageParam : 1;
  const searchKey = searchParams.toString();

  const [filters, setFilters] = useState(() => readFilters(searchParams, isGlobal));

  useEffect(() => {
    setFilters(readFilters(searchParams, isGlobal));
  }, [searchKey, isGlobal]);

  const loadData = async ({ showRefreshFeedback = false } = {}) => {
    if (data) setRefreshing(true);
    else setLoading(true);

    setError(null);
    try {
      const queryParams = buildRequestParams(searchParams, currentPage, isGlobal);

      if (isGlobal) {
        const [runs, overview, clients, hosts] = await Promise.all([
          getRuns(queryParams),
          getRunsOverview(queryParams),
          getClients({ limit: 500 }),
          getHosts({ limit: 500 }),
        ]);
        setData({
          context: null,
          runs: runs.items,
          total: runs.total,
          overview,
          clients: clients.items,
          hosts: hosts.items,
        });
      } else if (isAutomation) {
        const [automation, runs] = await Promise.all([
          getAutomationDetail(automationId),
          getAutomationRuns(automationId, queryParams),
        ]);
        setData({
          context: automation,
          runs: runs.items,
          total: runs.total,
          overview: null,
          clients: [],
          hosts: [],
        });
      } else {
        const runs = await getInstanceRuns(instanceId, queryParams);
        setData({
          context: null,
          runs: runs.items,
          total: runs.total,
          overview: null,
          clients: [],
          hosts: [],
        });
      }

      if (showRefreshFeedback) {
        setFeedback({
          type: 'success',
          message: isGlobal
            ? 'Histórico global de execuções atualizado.'
            : 'Histórico de execuções atualizado.',
        });
      }
    } catch (requestError) {
      setError(requestError);
    } finally {
      setLoading(false);
      setRefreshing(false);
      setSaving(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [searchKey, automationId, instanceId]);

  const runMetrics = useMemo(() => {
    if (isGlobal && data?.overview) {
      const statusSummary = deriveStatusMetrics(data.overview.status_counts);
      return {
        total: data.overview.total_runs || 0,
        running: statusSummary.running,
        completed: statusSummary.completed,
        failed: statusSummary.failed,
        stopped: statusSummary.stopped,
        unknown: statusSummary.unknown,
        logs: data.overview.total_logs || 0,
      };
    }

    const items = data?.runs || [];
    const statusSummary = {
      running: 0,
      completed: 0,
      failed: 0,
      stopped: 0,
      unknown: 0,
    };
    let logs = 0;

    items.forEach((run) => {
      statusSummary[normalizeStatus(run.status)] += 1;
      logs += Number(run.log_entries || 0);
    });

    return {
      total: data?.total || 0,
      running: statusSummary.running,
      completed: statusSummary.completed,
      failed: statusSummary.failed,
      stopped: statusSummary.stopped,
      unknown: statusSummary.unknown,
      logs,
    };
  }, [data, isGlobal]);

  const statusChartData = useMemo(
    () => [
      { name: 'Em execucao', key: 'running', value: runMetrics.running },
      { name: 'Concluidas', key: 'completed', value: runMetrics.completed },
      { name: 'Falhas', key: 'failed', value: runMetrics.failed },
      { name: 'Interrompidas', key: 'stopped', value: runMetrics.stopped },
      { name: 'Outras', key: 'unknown', value: runMetrics.unknown },
    ].filter((item) => item.value > 0),
    [runMetrics]
  );

  const dailyChartData = useMemo(
    () => (data?.overview?.runs_by_day || []).map((item) => ({ label: item.label, total: item.total })),
    [data]
  );

  const hourlyChartData = useMemo(
    () => fillHourlyChartData(data?.overview?.runs_by_hour || []),
    [data]
  );

  const hostOptions = useMemo(
    () =>
      (data?.hosts || []).map((host) => ({
        value: host.id,
        label: (host.display_name || host.hostname)
          ? `${host.display_name || host.hostname}${host.ip_address ? ` • ${host.ip_address}` : ''}`
          : host.ip_address || 'Maquina sem nome',
      })),
    [data]
  );

  const clientOptions = useMemo(
    () =>
      (data?.clients || []).map((client) => ({
        value: client.id,
        label: client.external_code ? `${client.name} • ${client.external_code}` : client.name,
      })),
    [data]
  );

  const columns = useMemo(() => {
    const baseColumns = [];

    if (isGlobal) {
      baseColumns.push({
        key: 'automation_name',
        header: 'Robo',
        render: (run) => (
          <div className="whitespace-nowrap">
            <Link className="font-semibold text-app-accent hover:underline" to={`/automations/${run.automation_id}/runs`}>
              {run.automation_name || 'Robo sem nome'}
            </Link>
            {run.automation_code ? (
              <span className="ml-1.5 text-[10px] text-app-muted">#{run.automation_code}</span>
            ) : null}
          </div>
        ),
      });
      baseColumns.push({
        key: 'client_name',
        header: 'Cliente',
        render: (run) =>
          run.client_id ? (
            <Link className="whitespace-nowrap text-app-accent hover:underline" to={`/clients/${run.client_id}`}>
              {run.client_name || 'Cliente'}
            </Link>
          ) : (
            <span className="text-app-muted">{run.client_name || 'N/D'}</span>
          ),
      });
      baseColumns.push({
        key: 'host_hostname',
        header: 'Maquina',
        render: (run) =>
          run.host_id ? (
            <Link className="whitespace-nowrap text-app-accent hover:underline" to={`/hosts/${run.host_id}`}>
              {run.host_display_name || run.host_hostname || run.host_ip || 'Host'}
            </Link>
          ) : (
            <span className="text-app-muted">{run.host_display_name || run.host_hostname || run.host_ip || 'N/D'}</span>
          ),
      });
    }

    baseColumns.push(
      {
        key: 'started_at',
        header: 'Inicio',
        render: (run) => (
          <span className="whitespace-nowrap text-app-text">{formatDateTime(run.started_at)}</span>
        ),
      },
      {
        key: 'finished_at',
        header: 'Fim',
        render: (run) => (
          <div className="whitespace-nowrap">
            {run.finished_at ? (
              <>
                <span className="text-app-text">{formatDateTime(run.finished_at)}</span>
                <span className="ml-1.5 text-[10px] text-app-muted">({formatDuration(run.started_at, run.finished_at)})</span>
              </>
            ) : (
              <span className="text-app-muted">—</span>
            )}
          </div>
        ),
      },
      {
        key: 'origin',
        header: 'Origem',
        headerClassName: 'text-center',
        cellClassName: 'text-center',
        render: (run) => {
          const isScheduled = run.origin === 'scheduler';
          return (
            <span
              title={isScheduled ? 'Agendado' : 'Manual'}
              className="inline-flex items-center justify-center"
            >
              {isScheduled
                ? <CalendarClock className="h-4 w-4 text-violet-400" />
                : <MousePointerClick className="h-4 w-4 text-sky-400" />}
            </span>
          );
        },
      },
      {
        key: 'status',
        header: 'Status',
        headerClassName: 'text-center',
        cellClassName: 'text-center',
        render: (run) => {
          const norm = normalizeStatus(run.status);
          const icons = {
            running:   { icon: <Activity className="h-4 w-4 text-amber-400 animate-pulse" />, label: 'Em execucao' },
            completed: { icon: <CheckCircle2 className="h-4 w-4 text-emerald-400" />, label: 'Concluido' },
            failed:    { icon: <AlertTriangle className="h-4 w-4 text-red-400" />, label: 'Erro' },
            stopped:   { icon: <Clock3 className="h-4 w-4 text-orange-400" />, label: 'Interrompido' },
            unknown:   { icon: <Clock3 className="h-4 w-4 text-app-muted" />, label: run.status || 'Desconhecido' },
          };
          const { icon, label } = icons[norm] || icons.unknown;
          return (
            <span title={label} className="inline-flex items-center justify-center">
              {icon}
            </span>
          );
        },
      },
      {
        key: 'log_entries',
        header: 'Logs',
        cellClassName: 'text-right tabular-nums text-app-muted text-xs',
        headerClassName: 'text-right',
      },
      {
        key: 'actions',
        header: '',
        cellClassName: 'text-right',
        render: (run) => (
          <Link
            to={`/runs/${run.id}`}
            className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-app-border text-app-muted transition hover:border-app-accent/40 hover:text-app-accent"
            title="Abrir detalhes"
          >
            <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        ),
      }
    );

    return baseColumns;
  }, [isGlobal]);

  const totalPages = Math.max(1, Math.ceil((data?.total || 0) / ITEMS_PER_PAGE));

  const applyFilters = (event) => {
    event.preventDefault();
    setSaving(true);
    const params = new URLSearchParams();

    if (isGlobal && filters.search.trim()) params.set('search', filters.search.trim());
    if (isGlobal && filters.client_id) params.set('client_id', filters.client_id);
    if (isGlobal && filters.host_id) params.set('host_id', filters.host_id);
    if (filters.status) params.set('status', filters.status);
    if (filters.started_after) params.set('started_after', parseDateTimeLocalToIso(filters.started_after));
    if (filters.started_before) params.set('started_before', parseDateTimeLocalToIso(filters.started_before));
    if (sortField !== 'started_at') params.set('sort_by', sortField);
    if (sortOrder !== 'desc') params.set('order', sortOrder);
    params.set('page', '1');

    setSearchParams(params);
  };

  const clearFilters = () => {
    setSaving(true);
    const params = new URLSearchParams();
    if (sortField !== 'started_at') params.set('sort_by', sortField);
    if (sortOrder !== 'desc') params.set('order', sortOrder);
    params.set('page', '1');
    setSearchParams(params);
  };

  const toggleSort = (field) => {
    const params = new URLSearchParams(searchParams);
    const currentField = params.get('sort_by') || 'started_at';
    const currentOrder = params.get('order') || 'desc';

    if (currentField === field) {
      params.set('order', currentOrder === 'asc' ? 'desc' : 'asc');
    } else {
      params.set('sort_by', field);
      params.set('order', field === 'log_entries' ? 'desc' : 'desc');
    }
    params.set('page', '1');
    setSearchParams(params);
  };

  const goToPage = (page) => {
    const params = new URLSearchParams(searchParams);
    params.set('page', String(page));
    setSearchParams(params);
  };

  useHeaderRefresh(() => loadData({ showRefreshFeedback: true }), refreshing);

  if (loading && !data) {
    return <LoadingState label={isGlobal ? 'Carregando historico global de execucoes...' : 'Carregando historico de execucoes...'} />;
  }

  if (error && !data) {
    return (
      <ErrorState
        title={error.title || 'Falha ao carregar execucoes'}
        message={getErrorMessage(error)}
        onRetry={() => loadData()}
        busy={refreshing}
      />
    );
  }

  const hasActiveFilters = Object.values(filters).some((value) => Boolean(value));
  const pageTitle = isGlobal
    ? 'Historico de execucoes'
    : isAutomation
      ? `Execucoes de ${data?.context?.name || 'automacao'}`
      : 'Execucoes da instancia';
  const pageSubtitle = isGlobal
    ? `Visao centralizada de todas as runs com filtros operacionais e leitura por periodo.${refreshing ? ' Atualizando...' : ''}`
    : isAutomation
      ? `Historico recente da automacao #${data?.context?.code || '-'}`
      : 'Historico recente da instancia selecionada';
  const backPath = isAutomation ? '/automations' : '/hosts';

  const metricsStrip = (
    <div className="flex flex-wrap items-center gap-2">
      <MetricChip icon={Activity} label="Total" value={runMetrics.total} tone="primary" iconClass="text-app-accent" />
      <MetricChip icon={Clock3} label="Executando" value={runMetrics.running} tone="warning" iconClass={runMetrics.running > 0 ? 'text-amber-500' : 'text-app-muted'} />
      <MetricChip icon={CheckCircle2} label="Concluidas" value={runMetrics.completed} tone="neutral" iconClass="text-emerald-500" />
      <MetricChip icon={AlertTriangle} label="Falhas" value={runMetrics.failed} tone="danger" iconClass={runMetrics.failed > 0 ? 'text-rose-500' : 'text-app-muted'} />
      <span className="mx-1 h-4 w-px bg-app-border/60" aria-hidden="true" />
      <MetricChip icon={FileText} label="Logs" value={runMetrics.logs} tone="neutral" iconClass="text-sky-500" />
    </div>
  );

  return (
    <>
      <PageHeader
        title={pageTitle}
        subtitle={pageSubtitle}
        actions={[
          !isGlobal ? (
            <Link
              key="back-runs"
              to={backPath}
              className="inline-flex items-center gap-2 rounded-xl border border-app-border px-3 py-2 text-sm text-app-muted transition hover:bg-app-primary/10"
            >
              <ArrowLeft className="h-4 w-4" /> Voltar
            </Link>
          ) : null,
        ].filter(Boolean)}
        extra={metricsStrip}
      />

      <SectionCard className="mb-6">
        <form onSubmit={applyFilters} className="flex flex-wrap items-center gap-2">
          {isGlobal ? (
            <div className="relative min-w-[180px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-app-muted" />
              <input
                type="text"
                value={filters.search}
                onChange={(event) => setFilters((current) => ({ ...current, search: event.target.value }))}
                placeholder="Buscar robo, cliente ou maquina"
                className="h-8 w-full rounded-lg border border-app-border bg-app-surface/60 py-1.5 pl-8 pr-3 text-xs text-app-text transition focus:border-app-accent"
              />
            </div>
          ) : null}

          {isGlobal ? (
            <select
              value={filters.client_id}
              onChange={(event) => setFilters((current) => ({ ...current, client_id: event.target.value }))}
              className="h-8 rounded-lg border border-app-border bg-app-surface/60 px-2.5 text-xs text-app-text transition focus:border-app-accent"
            >
              <option value="">Todos clientes</option>
              {clientOptions.map((client) => (
                <option key={client.value} value={client.value}>{client.label}</option>
              ))}
            </select>
          ) : null}

          {isGlobal ? (
            <select
              value={filters.host_id}
              onChange={(event) => setFilters((current) => ({ ...current, host_id: event.target.value }))}
              className="h-8 rounded-lg border border-app-border bg-app-surface/60 px-2.5 text-xs text-app-text transition focus:border-app-accent"
            >
              <option value="">Todas maquinas</option>
              {hostOptions.map((host) => (
                <option key={host.value} value={host.value}>{host.label}</option>
              ))}
            </select>
          ) : null}

          <select
            value={filters.status}
            onChange={(event) => setFilters((current) => ({ ...current, status: event.target.value }))}
            className="h-8 rounded-lg border border-app-border bg-app-surface/60 px-2.5 text-xs text-app-text transition focus:border-app-accent"
          >
            <option value="">Todos status</option>
            <option value="running">Em execucao</option>
            <option value="completed">Concluido</option>
            <option value="failed">Falha</option>
          </select>

          <div className="flex items-center gap-1 rounded-lg border border-app-border bg-app-surface/60 px-2.5">
            <span className="text-[10px] text-app-muted">De</span>
            <input
              type="datetime-local"
              value={filters.started_after}
              onChange={(event) => setFilters((current) => ({ ...current, started_after: event.target.value }))}
              className="h-8 bg-transparent text-xs text-app-text focus:outline-none"
            />
          </div>

          <div className="flex items-center gap-1 rounded-lg border border-app-border bg-app-surface/60 px-2.5">
            <span className="text-[10px] text-app-muted">Ate</span>
            <input
              type="datetime-local"
              value={filters.started_before}
              onChange={(event) => setFilters((current) => ({ ...current, started_before: event.target.value }))}
              className="h-8 bg-transparent text-xs text-app-text focus:outline-none"
            />
          </div>

          <BusyButton busy={saving} type="submit" className="h-8 px-3 py-0 text-xs">
            Aplicar
          </BusyButton>
          <button
            type="button"
            onClick={clearFilters}
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-app-border bg-app-surface text-app-muted transition hover:bg-app-primary/10"
            title="Limpar filtros"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </form>

        <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-app-border/40 pt-3">
          <span className="text-[10px] font-bold uppercase tracking-[0.12em] text-app-muted">Ordenar</span>
          <SortButton label="Inicio" field="started_at" sortField={sortField} sortOrder={sortOrder} onClick={toggleSort} />
          <SortButton label="Fim" field="finished_at" sortField={sortField} sortOrder={sortOrder} onClick={toggleSort} />
          <SortButton label="Logs" field="log_entries" sortField={sortField} sortOrder={sortOrder} onClick={toggleSort} />
          <span className="ml-auto text-xs text-app-muted">
            <span className="font-bold text-app-text">{(data?.total || 0).toLocaleString('pt-BR')}</span> execucoes
            {hasActiveFilters ? ' com filtros ativos' : ''}
          </span>
        </div>
      </SectionCard>

      {isGlobal ? (
        <section className="mb-6 grid gap-4 xl:grid-cols-12">
          <SectionCard title="Status" subtitle="Distribuicao do recorte" className="xl:col-span-2">
            {statusChartData.length ? (
              <div className="h-52 pt-1">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={statusChartData} dataKey="value" nameKey="name" innerRadius={34} outerRadius={56} strokeWidth={0}>
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
              <EmptyState title="Sem distribuicao" message="Nao ha execucoes suficientes para compor o grafico." />
            )}
          </SectionCard>

          <SectionCard title="Volume por dia" subtitle="Evolucao do volume dentro do recorte filtrado" className="xl:col-span-5">
            {dailyChartData.length ? (
              <div className="h-52 pt-1">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={dailyChartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <XAxis
                      dataKey="label"
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
                      cursor={{ fill: 'rgba(130,10,209,0.06)' }}
                    />
                    <Bar dataKey="total" fill="#820ad1" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState title="Sem volume diario" message="Ajuste o periodo para visualizar a distribuicao." />
            )}
          </SectionCard>

          <SectionCard title="Distribuicao por hora" subtitle="Concentracao das execucoes ao longo do dia" className="xl:col-span-5">
            {hourlyChartData.some((item) => item.total > 0) ? (
              <div className="h-52 pt-1">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={hourlyChartData} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
                    <defs>
                      <linearGradient id="hourlyGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#820ad1" stopOpacity={0.18} />
                        <stop offset="100%" stopColor="#820ad1" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis
                      dataKey="label"
                      stroke="#6d558d"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fontSize: 11, fill: '#6d558d' }}
                      interval={0}
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
                      fill="url(#hourlyGradient)"
                      dot={{ r: 3.5, fill: '#f0e6ff', stroke: '#820ad1', strokeWidth: 2 }}
                      activeDot={{ r: 5, fill: '#820ad1', stroke: '#f0e6ff', strokeWidth: 2 }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <EmptyState title="Sem distribuicao horaria" message="Nao ha dados suficientes para o grafico." />
            )}
          </SectionCard>
        </section>
      ) : null}

      {error ? (
        <div className="mb-6">
          <ErrorState
            title={error.title || 'Falha parcial'}
            message={getErrorMessage(error)}
            onRetry={() => loadData()}
            busy={refreshing}
          />
        </div>
      ) : null}

      <SectionCard
        title={isGlobal ? 'Lista paginada de execucoes' : 'Historico detalhado'}
        subtitle={isGlobal ? 'Todas as runs registradas com filtros, contexto e ordenacao operacional' : 'Listagem completa das execucoes no contexto selecionado'}
      >
        {data?.runs?.length ? (
          <div className="overflow-hidden rounded-xl border border-app-border bg-app-surface/40 shadow-sm">
            <DataTable columns={columns} rows={data.runs} rowKey={(row) => row.id} />
          </div>
        ) : (
          <EmptyState
            title="Nenhuma execucao encontrada"
            message={isGlobal ? 'Tente ajustar cliente, maquina, periodo ou o termo de busca.' : 'Experimente ajustar o status ou o periodo selecionado.'}
          />
        )}

        {totalPages > 1 ? (
          <div className="mt-6 flex flex-col gap-4 border-t border-app-border/40 pt-6 lg:flex-row lg:items-center lg:justify-between">
            <p className="text-xs text-app-muted">
              Mostrando{' '}
              <span className="font-bold text-app-text">{(currentPage - 1) * ITEMS_PER_PAGE + 1}</span>
              {' '}a{' '}
              <span className="font-bold text-app-text">{Math.min(currentPage * ITEMS_PER_PAGE, data?.total || 0)}</span>
              {' '}de{' '}
              <span className="font-bold text-app-text">{data?.total || 0}</span>
              {' '}execucoes
            </p>

            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  goToPage(currentPage - 1);
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                disabled={currentPage === 1}
                className="rounded-xl border border-app-border bg-app-surface px-4 py-2 text-xs font-bold text-app-muted transition hover:bg-app-primary/10 disabled:opacity-50"
              >
                Anterior
              </button>
              <button
                type="button"
                onClick={() => {
                  goToPage(currentPage + 1);
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                disabled={currentPage === totalPages}
                className="rounded-xl border border-app-border bg-app-surface px-4 py-2 text-xs font-bold text-app-muted transition hover:bg-app-primary/10 disabled:opacity-50"
              >
                Proxima
              </button>
            </div>
          </div>
        ) : null}
      </SectionCard>

      <FeedbackToast
        type={feedback?.type}
        message={feedback?.message}
        onClose={() => setFeedback(null)}
      />
    </>
  );
}

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
      <span className="font-bold">{typeof value === 'number' ? value.toLocaleString('pt-BR') : value}</span>
    </div>
  );
}

function SortButton({ label, field, sortField, sortOrder, onClick }) {
  const active = sortField === field;

  return (
    <button
      type="button"
      onClick={() => onClick(field)}
      className={`inline-flex items-center gap-2 rounded-lg border px-2.5 py-1 text-[10px] font-semibold transition ${active
        ? 'border-app-accent bg-app-accent/10 text-app-accent'
        : 'border-app-border bg-app-surface text-app-muted hover:border-app-muted'
        }`}
    >
      {label}
      {active ? (sortOrder === 'asc' ? <SortAsc className="h-3 w-3" /> : <SortDesc className="h-3 w-3" />) : null}
    </button>
  );
}

function buildRequestParams(searchParams, currentPage, isGlobal) {
  const params = {
    status: searchParams.get('status') || undefined,
    started_after: searchParams.get('started_after') || undefined,
    started_before: searchParams.get('started_before') || undefined,
    sort_by: searchParams.get('sort_by') || 'started_at',
    order: searchParams.get('order') || 'desc',
    limit: ITEMS_PER_PAGE,
    offset: (currentPage - 1) * ITEMS_PER_PAGE,
  };

  if (isGlobal) {
    params.search = searchParams.get('search') || undefined;
    params.client_id = searchParams.get('client_id') || undefined;
    params.host_id = searchParams.get('host_id') || undefined;
  }

  return params;
}

function readFilters(searchParams, isGlobal) {
  return {
    search: isGlobal ? searchParams.get('search') || '' : '',
    client_id: isGlobal ? searchParams.get('client_id') || '' : '',
    host_id: isGlobal ? searchParams.get('host_id') || '' : '',
    status: searchParams.get('status') || '',
    started_after: toDateTimeLocalValue(searchParams.get('started_after')),
    started_before: toDateTimeLocalValue(searchParams.get('started_before')),
  };
}

function deriveStatusMetrics(statusCounts = {}) {
  return Object.entries(statusCounts).reduce(
    (accumulator, [status, total]) => {
      accumulator[normalizeStatus(status)] += Number(total || 0);
      return accumulator;
    },
    { running: 0, completed: 0, failed: 0, stopped: 0, unknown: 0 }
  );
}

function fillHourlyChartData(hourlyBuckets) {
  const totals = new Map(hourlyBuckets.map((item) => [item.bucket, item.total]));
  return Array.from({ length: 24 }, (_, hour) => {
    const bucket = String(hour).padStart(2, '0');
    return {
      label: `${bucket}h`,
      total: totals.get(bucket) || 0,
    };
  });
}

function toDateTimeLocalValue(value) {
  if (!value) return '';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '';

  const year = parsed.getFullYear();
  const month = String(parsed.getMonth() + 1).padStart(2, '0');
  const day = String(parsed.getDate()).padStart(2, '0');
  const hours = String(parsed.getHours()).padStart(2, '0');
  const minutes = String(parsed.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function parseDateTimeLocalToIso(value) {
  if (!value) return '';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return '';
  return parsed.toISOString();
}

export default RunsPage;
