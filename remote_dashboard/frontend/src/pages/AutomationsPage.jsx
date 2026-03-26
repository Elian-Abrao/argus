import { Activity, ArrowRight, Bot, Building2, Cpu, HardDrive, Info, RefreshCw, Search } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import AutomationModal from '../components/AutomationModal';
import BusyButton from '../components/BusyButton';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import FeedbackToast from '../components/FeedbackToast';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import { getAgentStatus, getAutomations } from '../lib/api';
import { formatDateTime, getErrorMessage } from '../lib/format';
import useHeaderRefresh from '../layout/useHeaderRefresh';

function AutomationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [selectedAutomationId, setSelectedAutomationId] = useState(null);
  const [connectedHostIds, setConnectedHostIds] = useState(new Set());

  const searchKey = searchParams.toString();

  const loadData = async ({ showRefreshFeedback = false } = {}) => {
    if (data) setRefreshing(true);
    else setLoading(true);

    setError(null);
    try {
      const [payload, statusRes] = await Promise.all([
        getAutomations({ search: searchParams.get('search') || undefined }),
        getAgentStatus().catch(() => null),
      ]);
      setData(payload);
      if (statusRes?.items) {
        setConnectedHostIds(new Set(statusRes.items.filter((h) => h.connected).map((h) => h.host_id)));
      }
      if (showRefreshFeedback) {
        setFeedback({ type: 'success', message: 'Catalogo de robos atualizado.' });
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
    setSearch(searchParams.get('search') || '');
  }, [searchKey]);

  useEffect(() => {
    loadData();
  }, [searchKey]);

  const rows = useMemo(() => data?.items || [], [data]);

  const metrics = useMemo(() => {
    const instances = rows.reduce((acc, a) => acc + Number(a.instances_count || 0), 0);
    const hosts = rows.reduce((acc, a) => acc + Number(a.hosts_count || 0), 0);
    const clients = rows.reduce((acc, a) => acc + Number(a.clients_count || 0), 0);
    return { total: data?.total || 0, instances, hosts, clients };
  }, [rows, data]);

  const applySearch = (event) => {
    event.preventDefault();
    setSaving(true);
    const params = new URLSearchParams();
    if (search.trim()) params.set('search', search.trim());
    setSearchParams(params);
  };

  const clearSearch = () => {
    setSaving(true);
    setSearch('');
    setSearchParams({});
  };

  useHeaderRefresh(() => loadData({ showRefreshFeedback: true }), refreshing);

  if (loading && !data) {
    return <LoadingState label="Carregando catalogo de automacoes..." />;
  }

  if (error && !data) {
    return (
      <ErrorState
        title={error.title || 'Falha ao carregar catalogo'}
        message={getErrorMessage(error)}
        onRetry={() => loadData()}
        busy={refreshing}
      />
    );
  }

  const hasSearch = Boolean(searchParams.get('search'));

  const metricsStrip = (
    <div className="flex flex-wrap items-center gap-2">
      <MetricChip icon={Activity} label="Robos" value={metrics.total} tone="primary" iconClass="text-app-accent" />
      <MetricChip icon={Bot} label="Instancias" value={metrics.instances} tone="neutral" iconClass="text-emerald-500" />
      <MetricChip icon={HardDrive} label="Hosts" value={metrics.hosts} tone="neutral" iconClass="text-sky-500" />
      <MetricChip icon={Building2} label="Clientes" value={metrics.clients} tone="neutral" iconClass="text-violet-400" />
    </div>
  );

  return (
    <>
      <PageHeader
        title="Catalogo de Automacoes"
        subtitle={refreshing ? 'Atualizando...' : 'Robos cadastrados e suas instancias operacionais.'}
        extra={metricsStrip}
      />

      <SectionCard className="mb-6">
        <form onSubmit={applySearch} className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[200px] flex-1">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-app-muted" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar por nome ou codigo"
              className="h-8 w-full rounded-lg border border-app-border bg-app-surface/60 py-1.5 pl-8 pr-3 text-xs text-app-text transition focus:border-app-accent"
            />
          </div>
          <BusyButton busy={saving} type="submit" className="h-8 px-3 py-0 text-xs">
            Buscar
          </BusyButton>
          {hasSearch ? (
            <button
              type="button"
              onClick={clearSearch}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-app-border bg-app-surface text-app-muted transition hover:bg-app-primary/10"
              title="Limpar busca"
            >
              <RefreshCw className="h-3.5 w-3.5" />
            </button>
          ) : null}
          <span className="ml-auto text-xs text-app-muted">
            <span className="font-bold text-app-text">{(metrics.total).toLocaleString('pt-BR')}</span> robos
            {hasSearch ? ' encontrados' : ' cadastrados'}
          </span>
        </form>
      </SectionCard>

      {error ? (
        <div className="mb-4">
          <ErrorState title={error.title || 'Falha na busca'} message={getErrorMessage(error)} onRetry={() => loadData()} />
        </div>
      ) : null}

      {rows.length ? (
        <div className="overflow-hidden rounded-2xl border border-app-border bg-app-elevated/80 shadow-card">
          <table className="min-w-full divide-y divide-app-border text-sm">
            <thead>
              <tr>
                <th scope="col" className="w-4 px-2 py-2" />
                <th scope="col" className="whitespace-nowrap px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.08em] text-app-muted">Robo</th>
                <th scope="col" className="whitespace-nowrap px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.08em] text-app-muted">Equipe</th>
                <th scope="col" className="whitespace-nowrap px-3 py-2 text-center text-xs font-semibold uppercase tracking-[0.08em] text-app-muted">Instancias</th>
                <th scope="col" className="whitespace-nowrap px-3 py-2 text-center text-xs font-semibold uppercase tracking-[0.08em] text-app-muted">Hosts</th>
                <th scope="col" className="whitespace-nowrap px-3 py-2 text-center text-xs font-semibold uppercase tracking-[0.08em] text-app-muted">Clientes</th>
                <th scope="col" className="whitespace-nowrap px-3 py-2 text-left text-xs font-semibold uppercase tracking-[0.08em] text-app-muted">Ultima execucao</th>
                <th scope="col" className="px-3 py-2" />
              </tr>
            </thead>
            <tbody className="divide-y divide-app-border/80">
              {rows.map((automation) => (
                <tr
                  key={automation.id}
                  onClick={() => navigate(`/automations/${automation.id}/runs`)}
                  className="cursor-pointer transition hover:bg-app-primary/10"
                  title="Ver execucoes deste robo"
                >
                  <td className="w-4 px-2 py-2">
                    {(() => {
                      const isOnline = (automation.host_ids || []).some((hid) => connectedHostIds.has(hid));
                      return (
                        <span
                          className={`inline-block h-2 w-2 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-app-muted/30'}`}
                          title={isOnline ? 'Online' : 'Offline'}
                        />
                      );
                    })()}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2">
                    <div className="flex items-center gap-2.5">
                      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-app-primary/10 text-app-accent">
                        <Cpu className="h-4 w-4" />
                      </span>
                      <div>
                        <div className="font-semibold text-app-accent">{automation.name}</div>
                        <div className="text-[10px] text-app-muted">#{automation.code}</div>
                      </div>
                    </div>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-app-muted text-xs">
                    {automation.owner_team || 'N/D'}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-center">
                    <span className="inline-flex min-w-[1.75rem] items-center justify-center rounded-md bg-app-primary/10 px-1.5 py-0.5 text-xs font-bold text-app-accent">
                      {automation.instances_count}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-center">
                    <span className="inline-flex min-w-[1.75rem] items-center justify-center rounded-md bg-app-primary/10 px-1.5 py-0.5 text-xs font-bold text-app-accent">
                      {automation.hosts_count}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-center">
                    <span className="inline-flex min-w-[1.75rem] items-center justify-center rounded-md bg-app-primary/10 px-1.5 py-0.5 text-xs font-bold text-app-accent">
                      {automation.clients_count}
                    </span>
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-xs text-app-muted">
                    {automation.last_run_started_at ? formatDateTime(automation.last_run_started_at) : 'Nunca'}
                  </td>
                  <td className="whitespace-nowrap px-3 py-2 text-right">
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedAutomationId(automation.id);
                      }}
                      className="inline-flex h-7 w-7 items-center justify-center rounded-lg border border-app-border text-app-muted transition hover:border-app-accent/40 hover:text-app-accent"
                      title="Ver detalhes do robo"
                    >
                      <Info className="h-3.5 w-3.5" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="rounded-2xl border border-app-border bg-app-elevated/80 py-16">
          <EmptyState title="Nenhum robo encontrado" message="Altere os filtros de busca para localizar um robo especifico." />
        </div>
      )}

      {selectedAutomationId ? (
        <AutomationModal
          automationId={selectedAutomationId}
          onClose={() => setSelectedAutomationId(null)}
        />
      ) : null}

      <FeedbackToast type={feedback?.type} message={feedback?.message} onClose={() => setFeedback(null)} />
    </>
  );
}

function MetricChip({ icon: Icon, label, value, tone = 'neutral', iconClass = '' }) {
  const base = 'flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors';
  const tones = {
    neutral: 'text-app-muted bg-white border-app-border',
    primary: 'text-app-accent bg-app-primary/8 border-app-primary/25',
  };

  return (
    <div className={`${base} ${tones[tone] || tones.neutral}`}>
      <Icon className={`h-3 w-3 shrink-0 ${iconClass}`} />
      <span className="text-[11px] tracking-wide">{label}</span>
      <span className="font-bold">{typeof value === 'number' ? value.toLocaleString('pt-BR') : value}</span>
    </div>
  );
}

export default AutomationsPage;
