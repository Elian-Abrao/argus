import { Search, Users, Cpu, Database, Activity } from 'lucide-react';
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
import { getAgentStatus, getClients } from '../lib/api';
import { formatDateTime, getErrorMessage } from '../lib/format';
import useHeaderRefresh from '../layout/useHeaderRefresh';

function ClientsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [connectedHostIds, setConnectedHostIds] = useState(new Set());

  const searchKey = searchParams.toString();

  const loadData = async ({ showRefreshFeedback = false } = {}) => {
    if (data) setRefreshing(true);
    else setLoading(true);

    setError(null);
    try {
      const [payload, statusRes] = await Promise.all([
        getClients({ search: searchParams.get('search') || undefined }),
        getAgentStatus().catch(() => null),
      ]);
      setData(payload);
      if (statusRes?.items) {
        setConnectedHostIds(new Set(statusRes.items.filter((h) => h.connected).map((h) => h.host_id)));
      }
      if (showRefreshFeedback) {
        setFeedback({ type: 'success', message: 'Carteira de clientes atualizada.' });
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

  const columns = useMemo(
    () => [
      {
        key: 'online',
        header: '',
        cellClassName: 'w-4 pr-0',
        render: (client) => {
          const isOnline = (client.host_ids || []).some((hid) => connectedHostIds.has(hid));
          return (
            <span
              className={`inline-block h-2 w-2 rounded-full ${isOnline ? 'bg-emerald-500' : 'bg-app-muted/30'}`}
              title={isOnline ? 'Online' : 'Offline'}
            />
          );
        },
      },
      {
        key: 'name',
        header: 'Nome',
        headerClassName: "!text-[#2b114a]",
        cellClassName: "!text-[#6d558d]",
        render: (client) => (
          <Link className="font-semibold text-app-accent hover:underline" to={`/clients/${client.id}`}>
            {client.name}
          </Link>
        ),
      },
      { key: 'external_code', header: 'Codigo', headerClassName: "!text-[#2b114a]", cellClassName: "!text-[#6d558d]", render: (client) => client.external_code || 'N/D' },
      { key: 'contact_email', header: 'Contato', headerClassName: "!text-[#2b114a]", cellClassName: "!text-[#6d558d]", render: (client) => client.contact_email || 'N/D' },
      { key: 'automations_count', header: 'Robos', headerClassName: "!text-[#2b114a]", cellClassName: "!text-[#6d558d]" },
      { key: 'instances_count', header: 'Instancias', headerClassName: "!text-[#2b114a]", cellClassName: "!text-[#6d558d]" },
      {
        key: 'last_seen_at',
        header: 'Ultima atividade',
        headerClassName: "!text-[#2b114a]",
        cellClassName: "!text-[#6d558d]",
        render: (client) => formatDateTime(client.last_seen_at),
      },
    ],
    [connectedHostIds]
  );

  const clientMetrics = useMemo(() => {
    const items = data?.items || [];
    const automations = items.reduce(
      (accumulator, client) => accumulator + Number(client.automations_count || 0),
      0
    );
    const instances = items.reduce(
      (accumulator, client) => accumulator + Number(client.instances_count || 0),
      0
    );
    const withContact = items.filter((client) => client.contact_email).length;
    return {
      total: data?.total || 0,
      automations,
      instances,
      withContact,
    };
  }, [data]);

  const applySearch = (event) => {
    event.preventDefault();
    setSaving(true);
    const params = new URLSearchParams();
    if (search.trim()) params.set('search', search.trim());
    setSearchParams(params);
  };

  const clearSearch = () => {
    setSaving(true);
    setSearchParams({});
  };

  useHeaderRefresh(() => loadData({ showRefreshFeedback: true }), refreshing);

  if (loading && !data) {
    return <LoadingState label="Carregando carteira de clientes..." />;
  }

  if (error && !data) {
    return (
      <ErrorState
        title={error.title || 'Falha ao carregar clientes'}
        message={getErrorMessage(error)}
        onRetry={() => loadData()}
        busy={refreshing}
      />
    );
  }

  return (
    <>
      <PageHeader
        title="Carteira de clientes"
        subtitle={`${data?.total || 0} clientes cadastrados.${refreshing ? ' Atualizando...' : ''}`}
      />

      {/* Hero Header with Metrics & Compact Search */}
      <div className="mb-6 rounded-2xl border border-app-border bg-app-elevated/80 p-5 shadow-card flex flex-col xl:flex-row gap-6 justify-between items-start xl:items-center">
        {/* Compact Badges */}
        <div className="flex flex-wrap gap-3">
          <div className="flex items-center gap-2 rounded-lg bg-app-elevated/50 border border-app-border/40 px-3 py-1.5 shadow-sm">
            <Users className="h-4 w-4 text-app-accent" />
            <span className="text-xs text-[#2b114a] font-bold tracking-wide">Clientes:</span>
            <span className="text-sm font-bold text-[#6d558d]">{clientMetrics.total}</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg bg-app-elevated/50 border border-app-border/40 px-3 py-1.5 shadow-sm">
            <Activity className="h-4 w-4 text-emerald-500" />
            <span className="text-xs text-[#2b114a] font-bold tracking-wide">Robôs:</span>
            <span className="text-sm font-bold text-[#6d558d]">{clientMetrics.automations}</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg bg-app-elevated/50 border border-app-border/40 px-3 py-1.5 shadow-sm">
            <Database className="h-4 w-4 text-sky-500" />
            <span className="text-xs text-[#2b114a] font-bold tracking-wide">Instâncias:</span>
            <span className="text-sm font-bold text-[#6d558d]">{clientMetrics.instances}</span>
          </div>
          <div className="flex items-center gap-2 rounded-lg bg-app-elevated/50 border border-app-border/40 px-3 py-1.5 shadow-sm">
            <Users className="h-4 w-4 text-rose-500" />
            <span className="text-xs text-[#2b114a] font-bold tracking-wide">Com Contato:</span>
            <span className="text-sm font-bold text-[#6d558d]">{clientMetrics.withContact}</span>
          </div>
        </div>

        {/* Search */}
        <form onSubmit={applySearch} className="flex w-full xl:w-auto items-center gap-2 max-w-sm">
          <div className="relative w-full">
            <div className="pointer-events-none absolute inset-y-0 left-0 flex items-center pl-3">
              <Search className="h-4 w-4 text-app-muted" />
            </div>
            <input
              className="w-full rounded-xl border border-app-border bg-app-elevated/50 py-2 pl-9 pr-3 text-sm text-app-text outline-none transition focus:border-app-primary focus:ring-1 focus:ring-app-primary placeholder:text-gray-400 shadow-inner"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar cliente ou codigo..."
            />
          </div>
          {search && (
            <button
              type="button"
              onClick={clearSearch}
              className="text-xs text-[#6d558d] hover:text-[#2b114a] transition whitespace-nowrap px-1"
            >
              Limpar
            </button>
          )}
          <BusyButton busy={saving} type="submit" className="px-4 py-2 text-xs">
            Filtrar
          </BusyButton>
        </form>
      </div>

      {error ? (
        <div className="mb-4">
          <ErrorState title={error.title || 'Falha parcial'} message={getErrorMessage(error)} onRetry={() => loadData()} />
        </div>
      ) : null}

      <SectionCard title="Relacao de clientes" subtitle="Vinculos com automacoes e hosts">
        {data?.items?.length ? (
          <DataTable columns={columns} rows={data.items} rowKey={(row) => row.id} />
        ) : (
          <EmptyState title="Sem clientes" message="Nenhum cliente encontrado para os filtros atuais." />
        )}
      </SectionCard>

      <FeedbackToast type={feedback?.type} message={feedback?.message} onClose={() => setFeedback(null)} />
    </>
  );
}

export default ClientsPage;
