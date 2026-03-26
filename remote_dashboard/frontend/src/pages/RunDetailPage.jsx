import {
  ArrowLeft,
  Search,
  ArrowDownUp,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Mail,
  GitBranch,
  List,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams, useSearchParams } from 'react-router-dom';
import EmailCard from '../components/EmailCard';
import EmailDetailModal from '../components/EmailDetailModal';
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
} from 'recharts';
import BusyButton from '../components/BusyButton';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import FeedbackToast from '../components/FeedbackToast';
import FilterBar from '../components/FilterBar';
import LoadingState from '../components/LoadingState';
import MetricCard from '../components/MetricCard';
import SectionCard from '../components/SectionCard';
import StatusBadge from '../components/StatusBadge';
import { getEmailAttachmentUrl, getRunDetail, getRunEmails, getRunLogs, getRunLogsMetrics } from '../lib/api';
import ExecutionView from '../components/ExecutionView';
import {
  formatDateTime,
  formatTime,
  getErrorMessage,
  mapLevelColor,
  parseFlag,
} from '../lib/format';
import useHeaderRefresh from '../layout/useHeaderRefresh';

const ALL_LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];
const chartColorByLevel = {
  DEBUG: '#818cf8',
  INFO: '#38bdf8',
  WARNING: '#f59e0b',
  ERROR: '#fb7185',
  CRITICAL: '#d946ef',
};

const LOGS_PER_PAGE = 100;

function RunDetailPage() {
  const { runId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [metricsData, setMetricsData] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [selectedEmail, setSelectedEmail] = useState(null);
  const [viewMode, setViewMode] = useState('logs'); // 'logs' | 'trace'

  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');
  const [selectedLevels, setSelectedLevels] = useState(() => {
    const fromQuery = searchParams.getAll('level').map((value) => value.toUpperCase());
    return fromQuery.length ? fromQuery : ALL_LEVELS;
  });

  const searchKey = searchParams.toString();
  const searchFilter = searchParams.get('search') || undefined;
  const metaOpen = searchParams.get('meta') === 'open';
  const sortOrder = searchParams.get('sort') === 'desc' ? 'desc' : 'asc';

  const currentPageParams = parseInt(searchParams.get('page'), 10);
  const currentPage = !isNaN(currentPageParams) && currentPageParams > 0 ? currentPageParams : 1;

  const loadData = async ({ showRefreshFeedback = false } = {}) => {
    if (data) setRefreshing(true);
    else setLoading(true);

    setError(null);
    try {
      const [runResult, logsResult, metricsResult, emailsResult] = await Promise.allSettled([
        getRunDetail(runId),
        getRunLogs(runId, {
          search: searchFilter,
          limit: LOGS_PER_PAGE,
          offset: (currentPage - 1) * LOGS_PER_PAGE,
          sort: sortOrder,
        }),
        getRunLogsMetrics(runId),
        getRunEmails(runId, { limit: 50 }),
      ]);

      if (runResult.status === 'rejected') {
        throw runResult.reason;
      }
      if (logsResult.status === 'rejected') {
        throw logsResult.reason;
      }

      const run = runResult.value;
      const logs = logsResult.value;
      const metrics = metricsResult.status === 'fulfilled' ? metricsResult.value : null;
      const emails = emailsResult.status === 'fulfilled' ? emailsResult.value : null;

      setData({
        run,
        logs: logs.items,
        totalLogs: logs.total,
        emails: emails?.items || [],
        totalEmails: emails?.total || 0,
      });
      setMetricsData(metrics);

      const partialFailures = [];
      if (metricsResult.status === 'rejected') partialFailures.push('metricas');
      if (emailsResult.status === 'rejected') partialFailures.push('auditoria de e-mails');

      if (partialFailures.length > 0) {
        setFeedback({
          type: 'error',
          message: `Dados parciais: falha ao carregar ${partialFailures.join(' e ')}.`,
        });
      } else if (showRefreshFeedback) {
        setFeedback({ type: 'success', message: 'Logs atualizados com sucesso.' });
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
    const levelsFromQuery = searchParams.getAll('level').map((value) => value.toUpperCase());
    setSelectedLevels(levelsFromQuery.length ? levelsFromQuery : ALL_LEVELS);
    setSearchInput(searchParams.get('search') || '');
    // Resetting scroll implicitly when new page or search key changes and finishes loading (via useEffect layout or plain react render cycle)
  }, [searchKey]);

  useEffect(() => {
    loadData();
  }, [runId, searchKey]);

  const filteredLogs = useMemo(() => {
    const selectedSet = new Set(selectedLevels);
    return (data?.logs || []).filter((entry) => selectedSet.has(String(entry.level || '').toUpperCase()));
  }, [data, selectedLevels]);

  const levelMetrics = useMemo(() => {
    if (!metricsData) return null;

    const chartData = Object.entries(metricsData.counts)
      .filter(([, value]) => value > 0)
      .map(([level, value]) => ({ level, value }));

    const failures = (metricsData.counts.ERROR || 0) + (metricsData.counts.CRITICAL || 0);
    const warnings = metricsData.counts.WARNING || 0;

    // Process timeline for LineChart
    // Group timeline objects by Minute to reduce points on chart
    const timelineGroups = {};
    metricsData.timeline.forEach((item) => {
      const dt = new Date(item.ts);
      // Group by HH:MM
      const timeStr = `${String(dt.getHours()).padStart(2, '0')}:${String(dt.getMinutes()).padStart(2, '0')}`;
      if (!timelineGroups[timeStr]) {
        timelineGroups[timeStr] = { time: timeStr, DEBUG: 0, INFO: 0, WARNING: 0, ERROR: 0, CRITICAL: 0 };
      }
      timelineGroups[timeStr][item.level] += 1;
    });

    const lineChartData = Object.values(timelineGroups);
    // Also store cumulative offsets per time bucket for click-to-navigate
    let cumulative = 0;
    const timelineOffsets = {};
    for (const bucket of lineChartData) {
      const bucketTotal = (bucket.DEBUG || 0) + (bucket.INFO || 0) + (bucket.WARNING || 0) + (bucket.ERROR || 0) + (bucket.CRITICAL || 0);
      timelineOffsets[bucket.time] = cumulative; // offset BEFORE this bucket (first log ~= this page)
      cumulative += bucketTotal;
    }

    return {
      counters: metricsData.counts,
      chartData,
      lineChartData,
      timelineOffsets,
      total: metricsData.total,
      failures,
      warnings,
      failureRate:
        metricsData.total > 0
          ? Math.round((failures / metricsData.total) * 100)
          : 0,
    };
  }, [metricsData]);

  const parsedLogs = useMemo(
    () =>
      filteredLogs.map((entry) => {
        const { flagType, flagLines } = parseFlag(entry.message || '');
        const contextItems = extractItems(entry.context || {});
        const extraItems = extractItems(entry.extra || {}, ['plain', '_remote_sink_skip']);

        return {
          ...entry,
          flagType,
          flagLines,
          contextItems,
          extraItems,
          isMultiline: String(entry.message || '').includes('\n'),
          levelClass: String(entry.level || '').toUpperCase(),
        };
      }),
    [filteredLogs]
  );

  const totalPages = Math.ceil((data?.totalLogs || 0) / LOGS_PER_PAGE) || 1;
  const paginatedLogs = parsedLogs; // logs from backend are already sliced and sorted

  const toggleLevel = (level) => {
    setSelectedLevels((previous) => {
      if (previous.includes(level)) {
        const next = previous.filter((item) => item !== level);
        return next.length ? next : [level];
      }
      return [...previous, level];
    });
  };

  const applyFilters = (event) => {
    event.preventDefault();
    setSaving(true);
    const params = new URLSearchParams(searchParams);
    params.delete('level');
    selectedLevels.forEach((level) => params.append('level', level));

    if (searchInput.trim()) params.set('search', searchInput.trim());
    else params.delete('search');

    params.set('page', '1'); // Reset to page 1 on search
    setSearchParams(params);
  };

  const clearFilters = () => {
    setSaving(true);
    setSearchParams({});
  };

  const updateMeta = (open) => {
    const params = new URLSearchParams(searchParams);
    if (open) params.set('meta', 'open');
    else params.delete('meta');
    setSearchParams(params);
  };

  const toggleSort = () => {
    const params = new URLSearchParams(searchParams);
    params.set('sort', sortOrder === 'asc' ? 'desc' : 'asc');
    params.set('page', '1');
    setSearchParams(params);
  };

  const goToPage = (page) => {
    if (page < 1 || page > totalPages) return;
    const params = new URLSearchParams(searchParams);
    params.set('page', String(page));
    setSearchParams(params);
  };

  const handleTimelineClick = (chartEvent) => {
    if (!chartEvent?.activePayload || !levelMetrics?.timelineOffsets) return;
    const clickedTime = chartEvent.activePayload[0]?.payload?.time;
    if (!clickedTime) return;
    const offset = levelMetrics.timelineOffsets[clickedTime] ?? 0;
    const targetPage = Math.floor(offset / LOGS_PER_PAGE) + 1;
    goToPage(targetPage);
    // Scroll to the logs section
    setTimeout(() => {
      document.getElementById('logs-section')?.scrollIntoView({ behavior: 'smooth' });
    }, 200);
  };

  useHeaderRefresh(() => loadData({ showRefreshFeedback: true }), refreshing);

  if (loading && !data) {
    return <LoadingState label="Carregando detalhe de execucao e logs..." />;
  }

  if (error && !data) {
    return (
      <ErrorState
        title={error.title || 'Falha ao carregar run'}
        message={getErrorMessage(error)}
        onRetry={() => loadData()}
        busy={refreshing}
      />
    );
  }

  const run = data?.run;

  return (
    <>
      {error ? (
        <div className="mb-4">
          <ErrorState title={error.title || 'Falha parcial'} message={getErrorMessage(error)} onRetry={() => loadData()} />
        </div>
      ) : null}

      {/* Header and Filters Bar - Dense and Operational */}
      <div className="mb-4 flex flex-col justify-between gap-3 lg:flex-row lg:items-center rounded-xl border border-app-border bg-app-elevated/80 p-3 shadow-card">
        <div className="flex items-center gap-3">
          <Link
            to={run?.automation_id ? `/automations/${run.automation_id}/runs` : '/automations'}
            className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-app-border bg-app-primary/10 text-app-muted transition hover:bg-app-primary/20 hover:text-app-text"
            title="Voltar"
          >
            <ArrowLeft className="h-4 w-4" />
          </Link>
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <h1 className="text-sm font-semibold text-app-text">
                {run?.automation_name || 'Execucao'}
              </h1>
              <StatusBadge status={run?.status} />
            </div>
            <p className="text-[10px] text-app-muted">
              {formatDateTime(run?.started_at)} • Host: {run?.host_display_name || run?.host_hostname || 'Desconhecido'} • {data?.totalLogs || 0} logs totais
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">

          {/* View mode toggle */}
          <div className="flex items-center gap-1 rounded-lg border border-app-border bg-app-primary/5 p-1">
            <button
              onClick={() => setViewMode('logs')}
              className={`flex items-center gap-1 px-2.5 py-1 text-[10px] font-bold uppercase rounded transition-colors ${viewMode === 'logs' ? 'bg-app-accent text-white' : 'text-app-muted hover:bg-app-primary/20 hover:text-app-text'}`}
            >
              <List className="h-3 w-3" /> Logs
            </button>
            <button
              onClick={() => setViewMode('trace')}
              className={`flex items-center gap-1 px-2.5 py-1 text-[10px] font-bold uppercase rounded transition-colors ${viewMode === 'trace' ? 'bg-app-accent text-white' : 'text-app-muted hover:bg-app-primary/20 hover:text-app-text'}`}
            >
              <GitBranch className="h-3 w-3" /> Execução
            </button>
          </div>

          {/* Log-only controls */}
          {viewMode === 'logs' && (
            <>
              <div className="flex items-center gap-1 rounded-lg border border-app-border bg-app-primary/5 p-1">
                {ALL_LEVELS.map((level) => {
                  const checked = selectedLevels.includes(level);
                  return (
                    <button
                      key={level}
                      onClick={() => toggleLevel(level)}
                      className={`px-2 py-1 text-[10px] font-bold uppercase rounded transition-colors ${checked ? 'bg-app-accent text-white' : 'text-app-muted hover:bg-app-primary/20 hover:text-app-text'}`}
                    >
                      {level.substring(0, 3)}
                    </button>
                  );
                })}
              </div>

              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Buscar log na pag..."
                className="h-8 max-w-[150px] rounded-lg border border-app-border bg-app-primary/5 px-3 text-xs text-app-text placeholder-app-muted focus:border-app-accent focus:outline-none"
                onKeyDown={(e) => e.key === 'Enter' && applyFilters(e)}
              />

              <BusyButton busy={saving} onClick={applyFilters} className="h-8 px-3 text-xs">
                <Search className="mr-1 h-3 w-3" /> Aplicar
              </BusyButton>

              <button onClick={toggleSort} className="flex h-8 w-8 items-center justify-center rounded-lg border border-app-border bg-app-primary/5 text-app-muted hover:bg-app-primary/20" title="Inverter Ordem">
                <ArrowDownUp className="h-4 w-4" />
              </button>
              <button onClick={() => updateMeta(!metaOpen)} className="flex h-8 items-center justify-center rounded-lg border border-app-border bg-app-primary/5 px-3 text-xs font-semibold text-app-muted hover:bg-app-primary/20">
                {metaOpen ? 'Recolher CTX' : 'Expandir CTX'}
              </button>
            </>
          )}

        </div>
      </div>

      {/* Mini Charts Bar */}
      <div className="mb-4 grid gap-4 lg:grid-cols-4">
        {/* Pie Chart & Quick Stats */}
        <div className="rounded-xl border border-app-border bg-app-elevated/80 p-4 lg:col-span-1 flex items-center justify-between shadow-card">
          <div className="h-28 w-1/2">
            {levelMetrics?.chartData?.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={levelMetrics.chartData} dataKey="value" nameKey="level" outerRadius={45} innerRadius={28}>
                    {levelMetrics.chartData.map((entry) => (
                      <Cell key={entry.level} fill={chartColorByLevel[entry.level]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#1e1e2e', borderColor: '#3b2f56', borderRadius: '8px', color: '#f4f4f5', fontSize: '11px' }} itemStyle={{ padding: 0, color: '#f4f4f5' }} labelStyle={{ color: '#a1a1aa' }} />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-[10px] text-app-muted">Sem dados</div>
            )}
          </div>
          <div className="w-1/2 flex flex-col gap-2 pl-4 border-l border-app-border/40 justify-center text-sm">
            <div className="text-app-muted">Total: <span className="font-semibold text-app-text">{levelMetrics?.total || 0}</span></div>
            <div className="text-app-muted">Erros: <span className="font-semibold text-rose-500">{levelMetrics?.failures || 0}</span></div>
            <div className="text-app-muted">Warns: <span className="font-semibold text-amber-500">{levelMetrics?.warnings || 0}</span></div>
          </div>
        </div>

        {/* Timeline Chart */}
        <div className="rounded-xl border border-app-border bg-app-elevated/80 p-4 lg:col-span-3 flex flex-col justify-between shadow-card">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-bold uppercase tracking-[0.1em] text-app-muted">Timeline de logs (Global)</span>
            <span className="text-[10px] text-app-muted italic">Clique para ir aos logs daquele momento</span>
          </div>
          <div className="h-32 w-full cursor-pointer">
            {levelMetrics?.lineChartData?.length ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={levelMetrics.lineChartData} margin={{ top: 2, right: 5, left: -25, bottom: 0 }} onClick={handleTimelineClick}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#cacaca15" vertical={false} />
                  <XAxis dataKey="time" stroke="#8b8b8b" fontSize={11} tickMargin={5} minTickGap={20} tickLine={false} axisLine={false} />
                  <YAxis stroke="#8b8b8b" fontSize={11} tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: '#1e1e2e', borderColor: '#3b2f56', borderRadius: '8px', color: '#f4f4f5', fontSize: '11px' }} itemStyle={{ padding: 0 }} />
                  <Line type="monotone" dataKey="CRITICAL" stroke="#e30000" strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="ERROR" stroke="#fc4a03" strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="WARNING" stroke="#fc6f03" strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="INFO" stroke="#22c55e" strokeWidth={2} dot={false} isAnimationActive={false} />
                  <Line type="monotone" dataKey="DEBUG" stroke="#3b82f6" strokeWidth={2} dot={false} isAnimationActive={false} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-full items-center justify-center text-[10px] text-app-muted">Sem historico</div>
            )}
          </div>
        </div>
      </div >

      <SectionCard
        title="Auditoria de e-mails enviados"
        subtitle={`Eventos capturados via smtplib nesta execucao: ${data?.totalEmails || 0}`}
        icon={<Mail className="h-5 w-5" />}
      >
        {data?.emails?.length ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {data.emails.map((emailEvent) => (
              <EmailCard
                key={emailEvent.id}
                email={emailEvent}
                active={selectedEmail?.id === emailEvent.id}
                onClick={setSelectedEmail}
              />
            ))}
          </div>
        ) : (
          <EmptyState
            title="Sem e-mails capturados"
            message="Nenhum envio via smtplib foi registrado para esta execucao."
          />
        )}
      </SectionCard>

      {viewMode === 'trace' && (
        <SectionCard
          id="logs-section"
          title="Reconstrução da Execução"
          subtitle="Fluxo de execução reconstruído a partir dos logs e call chains."
          icon={<GitBranch className="h-5 w-5" />}
        >
          <ExecutionView key={runId} runId={runId} runStartTs={run?.started_at} />
        </SectionCard>
      )}

      {viewMode === 'logs' && <SectionCard
        id="logs-section"
        title="Visualizacao de logs"
        subtitle={`Mostrando ${paginatedLogs.length} logs na pagina ${currentPage} (Total filtrado/banco: ${data?.totalLogs || 0})`}
        actions={
          totalPages > 1 ? (
            <div className="flex items-center gap-2">
              <span className="text-xs text-app-muted mr-2">Pagina {currentPage} de {totalPages}</span>
              <button
                type="button"
                onClick={() => goToPage(1)}
                disabled={currentPage === 1}
                className="inline-flex items-center gap-1 rounded-lg border border-app-border px-2 py-1.5 text-xs font-medium text-app-text transition hover:bg-app-primary/10 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Primeira pagina"
              >
                <ChevronsLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => goToPage(currentPage - 1)}
                disabled={currentPage === 1}
                className="inline-flex items-center gap-1 rounded-lg border border-app-border px-2 py-1.5 text-xs font-medium text-app-text transition hover:bg-app-primary/10 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4" />
                Anterior
              </button>
              <button
                type="button"
                onClick={() => goToPage(currentPage + 1)}
                disabled={currentPage === totalPages}
                className="inline-flex items-center gap-1 rounded-lg border border-app-border px-2 py-1.5 text-xs font-medium text-app-text transition hover:bg-app-primary/10 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Proxima
                <ChevronRight className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => goToPage(totalPages)}
                disabled={currentPage === totalPages}
                className="inline-flex items-center gap-1 rounded-lg border border-app-border px-2 py-1.5 text-xs font-medium text-app-text transition hover:bg-app-primary/10 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Ultima pagina"
              >
                <ChevronsRight className="h-4 w-4" />
              </button>
            </div>
          ) : null
        }
      >
        {paginatedLogs.length ? (
          <div className="flex flex-col gap-px overflow-x-auto rounded-xl border border-app-border bg-[#0a0a0a]/80 shadow-card p-2 text-[11px] font-mono leading-relaxed text-gray-300">
            {paginatedLogs.map((entry) => {
              const LvlColor =
                entry.levelClass === 'ERROR' || entry.levelClass === 'CRITICAL' ? 'text-rose-400'
                  : entry.levelClass === 'WARNING' ? 'text-amber-400'
                    : 'text-sky-400';

              return (
                <div
                  key={`${entry.sequence}-${entry.ts}`}
                  className="group flex flex-col gap-1 rounded py-1 px-2 hover:bg-white/5"
                >
                  <div className="flex items-start gap-3 whitespace-nowrap">
                    <span className="w-16 text-right tabular-nums text-gray-600">#{entry.sequence}</span>
                    <span className="text-gray-500">{formatTime(entry.ts)}</span>
                    <span className={`w-16 font-semibold ${LvlColor}`}>{entry.levelClass}</span>

                    <span className="pr-2 text-wrap break-words text-gray-200">
                      {entry.flagType ? (
                        <span className="font-bold uppercase tracking-wider text-emerald-400">
                          [{entry.flagType === 'start' ? 'Process Start' : 'Process End'}]
                          <span className="ml-1 font-normal text-gray-300">
                            {entry.flagLines.join(' | ')}
                          </span>
                        </span>
                      ) : entry.message}
                    </span>
                  </div>

                  {(entry.contextItems.length > 0 || entry.extraItems.length > 0) && (
                    <div className="pl-[8.5rem]">
                      <details open={metaOpen} className="group/details">
                        <summary className="flex cursor-pointer select-none list-none items-center gap-1 pb-1 text-gray-500 hover:text-gray-300">
                          <ChevronRight className="inline-block h-3 w-3 transition-transform group-open/details:rotate-90" />
                          <span className="opacity-70">Detalhes extras</span>
                        </summary>
                        <div className="mt-1 flex flex-col gap-1 border-l border-gray-700/50 pl-2 opacity-80">
                          {entry.contextItems.map((item) => (
                            <div key={`${entry.sequence}-ctx-${item.label}`} className="text-wrap break-words">
                              <span className="text-emerald-300/80">ctx.{item.label}: </span>
                              <span>{String(item.value)}</span>
                            </div>
                          ))}
                          {entry.extraItems.map((item) => (
                            <div key={`${entry.sequence}-extra-${item.label}`} className="text-wrap break-words">
                              <span className="text-purple-300/80">extra.{item.label}: </span>
                              <span>{String(item.value)}</span>
                            </div>
                          ))}
                        </div>
                      </details>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        ) : (
          <EmptyState title="Sem logs" message="Nao foram encontrados logs para os filtros selecionados." />
        )}

        {totalPages > 1 ? (
          <div className="mt-6 flex items-center justify-between border-t border-app-border/40 pt-4">
            <span className="text-sm text-app-muted">
              Mostrando logs {(currentPage - 1) * LOGS_PER_PAGE + 1} ate {Math.min(currentPage * LOGS_PER_PAGE, data?.totalLogs || 0)} de {data?.totalLogs || 0}
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={() => {
                  goToPage(1);
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                disabled={currentPage === 1}
                className="inline-flex items-center gap-1 rounded-xl border border-app-border px-4 py-2 text-sm font-medium text-app-text transition hover:bg-app-primary/10 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Primeira pagina"
              >
                <ChevronsLeft className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => {
                  goToPage(currentPage - 1);
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                disabled={currentPage === 1}
                className="inline-flex items-center gap-1 rounded-xl border border-app-border px-4 py-2 text-sm font-medium text-app-text transition hover:bg-app-primary/10 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="h-4 w-4" />
                Anterior
              </button>
              <button
                type="button"
                onClick={() => {
                  goToPage(currentPage + 1);
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                disabled={currentPage === totalPages}
                className="inline-flex items-center gap-1 rounded-xl border border-app-border px-4 py-2 text-sm font-medium text-app-text transition hover:bg-app-primary/10 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Proxima
                <ChevronRight className="h-4 w-4" />
              </button>
              <button
                type="button"
                onClick={() => {
                  goToPage(totalPages);
                  window.scrollTo({ top: 0, behavior: 'smooth' });
                }}
                disabled={currentPage === totalPages}
                className="inline-flex items-center gap-1 rounded-xl border border-app-border px-4 py-2 text-sm font-medium text-app-text transition hover:bg-app-primary/10 disabled:opacity-50 disabled:cursor-not-allowed"
                title="Ultima pagina"
              >
                <ChevronsRight className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : null}
      </SectionCard>}

      <FeedbackToast type={feedback?.type} message={feedback?.message} onClose={() => setFeedback(null)} />

      {selectedEmail && (
        <EmailDetailModal
          email={selectedEmail}
          onClose={() => setSelectedEmail(null)}
        />
      )}
    </>
  );
}

function extractItems(source, keysToIgnore = []) {
  if (!source || typeof source !== 'object') return [];
  const ignore = new Set(keysToIgnore);

  return Object.entries(source)
    .filter(([key]) => !ignore.has(key))
    .map(([key, value]) => {
      if (key === 'call_chain' && typeof value === 'string') {
        return {
          label: 'call_chain',
          value: value.replace(/>/g, ' -> '),
        };
      }
      if (key === 'pathname' && source.lineno) {
        return {
          label: 'arquivo',
          value: `${value}:${source.lineno}`,
        };
      }
      return {
        label: key,
        value,
      };
    })
    .filter((item, index, array) => {
      if (item.label !== 'lineno') return true;
      return !array.some((candidate) => candidate.label === 'arquivo');
    });
}

export default RunDetailPage;

function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return '0 B';
  const value = Number(bytes);
  if (!Number.isFinite(value) || value <= 0) return '0 B';
  if (value < 1024) return `${value} B`;
  const units = ['KB', 'MB', 'GB'];
  let size = value / 1024;
  let unitIndex = 0;
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }
  return `${size.toFixed(size >= 10 ? 0 : 1)} ${units[unitIndex]}`;
}
