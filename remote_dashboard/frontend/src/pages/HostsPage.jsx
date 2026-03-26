import { Search, Server, Activity, Database, Box, Layers } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import BusyButton from '../components/BusyButton';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import FeedbackToast from '../components/FeedbackToast';
import LoadingState from '../components/LoadingState';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import { getAgentStatus, getHosts } from '../lib/api';
import { formatDateTime, getErrorMessage } from '../lib/format';
import useHeaderRefresh from '../layout/useHeaderRefresh';

function HostsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [connectedHostIds, setConnectedHostIds] = useState(new Set());

  const [filters, setFilters] = useState(() => readFilters(searchParams));

  const searchKey = searchParams.toString();

  const loadData = async ({ showRefreshFeedback = false } = {}) => {
    if (data) setRefreshing(true);
    else setLoading(true);

    setError(null);
    try {
      const [payload, statusRes] = await Promise.all([
        getHosts({
          search: searchParams.get('search') || undefined,
          hostname: searchParams.get('hostname') || undefined,
          ip_address: searchParams.get('ip_address') || undefined,
          environment: searchParams.get('environment') || undefined,
        }),
        getAgentStatus().catch(() => null),
      ]);
      setData(payload);
      if (statusRes?.items) {
        setConnectedHostIds(new Set(statusRes.items.filter((h) => h.connected).map((h) => h.host_id)));
      }
      if (showRefreshFeedback) {
        setFeedback({ type: 'success', message: 'Inventario atualizado.' });
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
    setFilters(readFilters(searchParams));
  }, [searchKey]);

  useEffect(() => {
    loadData();
  }, [searchKey]);

  const environmentOptions = useMemo(() => {
    const values = new Set();
    (data?.items || []).forEach((host) => {
      if (host.environment) values.add(host.environment);
    });
    return [...values].sort((left, right) => left.localeCompare(right));
  }, [data]);

  const columns = useMemo(
    () => [
      {
        key: 'online',
        header: '',
        cellClassName: 'w-4 pr-0',
        render: (host) => (
          <span
            className={`inline-block h-2 w-2 rounded-full ${connectedHostIds.has(host.id) ? 'bg-emerald-500' : 'bg-app-muted/30'}`}
            title={connectedHostIds.has(host.id) ? 'Online' : 'Offline'}
          />
        ),
      },
      {
        key: 'hostname',
        header: 'Maquina',
        headerClassName: "!text-[#2b114a]",
        cellClassName: "!text-[#6d558d]",
        render: (host) => (
          <Link className="font-semibold text-app-accent hover:underline" to={`/hosts/${host.id}`}>
            {host.display_name || host.hostname || 'Sem nome'}
            {host.display_name && host.hostname && (
              <span className="ml-1.5 text-[10px] text-app-muted font-normal">({host.hostname})</span>
            )}
          </Link>
        ),
      },
      { key: 'ip_address', header: 'IP', headerClassName: "!text-[#2b114a]", cellClassName: "!text-[#6d558d]", render: (host) => host.ip_address || 'N/D' },
      { key: 'environment', header: 'Ambiente', headerClassName: "!text-[#2b114a]", cellClassName: "!text-[#6d558d]", render: (host) => host.environment || 'N/D' },
      { key: 'root_folder', header: 'Raiz', headerClassName: "!text-[#2b114a]", cellClassName: "!text-[#6d558d]", render: (host) => host.root_folder || '-' },
      { key: 'automation_count', header: 'Robos', headerClassName: "!text-[#2b114a]", cellClassName: "!text-[#6d558d]" },
      {
        key: 'last_seen_at',
        header: 'Ultimo contato',
        headerClassName: "!text-[#2b114a]",
        cellClassName: "!text-[#6d558d]",
        render: (host) => formatDateTime(host.last_seen_at),
      },
    ],
    [connectedHostIds]
  );

  const hostMetrics = useMemo(() => {
    const items = data?.items || [];
    const automationTotal = items.reduce(
      (accumulator, host) => accumulator + Number(host.automation_count || 0),
      0
    );
    const environments = new Set(
      items.map((host) => host.environment).filter(Boolean)
    );
    const withIp = items.filter((host) => host.ip_address).length;
    return {
      hosts: data?.total || 0,
      automationTotal,
      environments: environments.size,
      withIp,
    };
  }, [data]);

  const applyFilters = (event) => {
    event.preventDefault();
    setSaving(true);
    const params = new URLSearchParams();
    if (filters.search.trim()) params.set('search', filters.search.trim());
    if (filters.hostname.trim()) params.set('hostname', filters.hostname.trim());
    if (filters.ip_address.trim()) params.set('ip_address', filters.ip_address.trim());
    if (filters.environment.trim()) params.set('environment', filters.environment.trim());
    setSearchParams(params);
  };

  const clearFilters = () => {
    setSaving(true);
    setSearchParams({});
  };

  useHeaderRefresh(() => loadData({ showRefreshFeedback: true }), refreshing);

  if (loading && !data) {
    return <LoadingState label="Carregando inventario de maquinas..." />;
  }

  if (error && !data) {
    return (
      <ErrorState
        title={error.title || 'Falha ao carregar hosts'}
        message={getErrorMessage(error)}
        onRetry={() => loadData()}
        busy={refreshing}
      />
    );
  }

  return (
    <>
      <PageHeader
        title="Inventario de maquinas"
        subtitle={`${data?.total || 0} maquinas registradas.${refreshing ? ' Atualizando...' : ''}`}
      />

      {/* Hero Header with Metrics & Compact Filters */}
      <div className="mb-6 rounded-2xl border border-app-border bg-app-elevated/80 p-5 shadow-card flex flex-col gap-6">
        <div className="flex flex-col xl:flex-row gap-6 justify-between items-start xl:items-center w-full">
          {/* Compact Badges */}
          <div className="flex flex-wrap gap-3">
            <div className="flex items-center gap-2 rounded-lg bg-app-elevated/50 border border-app-border/40 px-3 py-1.5 shadow-sm">
              <Server className="h-4 w-4 text-app-accent" />
              <span className="text-xs text-[#2b114a] font-bold tracking-wide">Máquinas:</span>
              <span className="text-sm font-bold text-[#6d558d]">{hostMetrics.hosts}</span>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-app-elevated/50 border border-app-border/40 px-3 py-1.5 shadow-sm">
              <Activity className="h-4 w-4 text-emerald-500" />
              <span className="text-xs text-[#2b114a] font-bold tracking-wide">Robôs:</span>
              <span className="text-sm font-bold text-[#6d558d]">{hostMetrics.automationTotal}</span>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-app-elevated/50 border border-app-border/40 px-3 py-1.5 shadow-sm">
              <Layers className="h-4 w-4 text-sky-500" />
              <span className="text-xs text-[#2b114a] font-bold tracking-wide">Ambientes:</span>
              <span className="text-sm font-bold text-[#6d558d]">{hostMetrics.environments}</span>
            </div>
            <div className="flex items-center gap-2 rounded-lg bg-app-elevated/50 border border-app-border/40 px-3 py-1.5 shadow-sm">
              <Database className="h-4 w-4 text-rose-500" />
              <span className="text-xs text-[#2b114a] font-bold tracking-wide">Hosts com IP:</span>
              <span className="text-sm font-bold text-[#6d558d]">{hostMetrics.withIp}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 self-end xl:self-auto">
            {Object.values(filters).some(v => v !== '') && (
              <button
                type="button"
                onClick={clearFilters}
                className="text-xs text-[#6d558d] hover:text-[#2b114a] transition whitespace-nowrap px-2"
              >
                Limpar Filtros
              </button>
            )}
          </div>
        </div>

        {/* Multi-Filter Bar */}
        <form onSubmit={applyFilters} className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-3 w-full border-t border-app-border/30 pt-4">
          <div className="relative">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <Search className="h-4 w-4 text-app-muted" />
            </div>
            <input
              className="w-full rounded-xl border border-app-border bg-app-elevated/50 py-2 pl-9 pr-3 text-sm text-app-text outline-none transition focus:border-app-primary focus:ring-1 focus:ring-app-primary placeholder:text-gray-400 shadow-inner"
              value={filters.search}
              onChange={(e) => setFilters(prev => ({ ...prev, search: e.target.value }))}
              placeholder="Busca geral..."
            />
          </div>
          <input
            className="w-full rounded-xl border border-app-border bg-app-elevated/50 py-2 px-3 text-sm text-app-text outline-none transition focus:border-app-primary focus:ring-1 focus:ring-app-primary placeholder:text-gray-400 shadow-inner"
            value={filters.hostname}
            onChange={(e) => setFilters(prev => ({ ...prev, hostname: e.target.value }))}
            placeholder="Hostname..."
          />
          <input
            className="w-full rounded-xl border border-app-border bg-app-elevated/50 py-2 px-3 text-sm text-app-text outline-none transition focus:border-app-primary focus:ring-1 focus:ring-app-primary placeholder:text-gray-400 shadow-inner"
            value={filters.ip_address}
            onChange={(e) => setFilters(prev => ({ ...prev, ip_address: e.target.value }))}
            placeholder="Endereço IP..."
          />
          <select
            className="w-full rounded-xl border border-app-border bg-app-elevated/50 py-2 px-3 text-sm text-app-text outline-none transition focus:border-app-primary focus:ring-1 focus:ring-app-primary shadow-inner appearance-none cursor-pointer"
            value={filters.environment}
            onChange={(e) => setFilters(prev => ({ ...prev, environment: e.target.value }))}
          >
            <option value="">Todos Ambientes</option>
            {environmentOptions.map(opt => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
          <BusyButton busy={saving} type="submit" className="w-full py-2 text-xs h-[38px]">
            Aplicar Filtros
          </BusyButton>
        </form>
      </div>

      {error ? (
        <div className="mb-4">
          <ErrorState title={error.title || 'Falha parcial'} message={getErrorMessage(error)} onRetry={() => loadData()} />
        </div>
      ) : null}

      <SectionCard title="Relacao de maquinas" subtitle="Visao consolidada de hosts e robos vinculados">
        {data?.items?.length ? (
          <DataTable columns={columns} rows={data.items} rowKey={(row) => row.id} emptyMessage="Nenhuma maquina encontrada." />
        ) : (
          <EmptyState title="Nenhuma maquina encontrada" message="Ajuste os filtros e tente novamente." />
        )}
      </SectionCard>

      <FeedbackToast type={feedback?.type} message={feedback?.message} onClose={() => setFeedback(null)} />
    </>
  );
}

function readFilters(searchParams) {
  return {
    search: searchParams.get('search') || '',
    hostname: searchParams.get('hostname') || '',
    ip_address: searchParams.get('ip_address') || '',
    environment: searchParams.get('environment') || '',
  };
}

export default HostsPage;
