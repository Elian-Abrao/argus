import { ArrowLeft, Pencil, Check, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import DataTable from '../components/DataTable';
import EmptyState from '../components/EmptyState';
import ErrorState from '../components/ErrorState';
import FeedbackToast from '../components/FeedbackToast';
import LoadingState from '../components/LoadingState';
import MetricCard from '../components/MetricCard';
import PageHeader from '../components/PageHeader';
import SectionCard from '../components/SectionCard';
import { getHostDetail, getHostInstances, updateHost } from '../lib/api';
import { formatDateTime, getErrorMessage } from '../lib/format';
import useHeaderRefresh from '../layout/useHeaderRefresh';

function HostDetailPage() {
  const { hostId } = useParams();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState('');
  const [nameSaving, setNameSaving] = useState(false);

  const loadData = async ({ showRefreshFeedback = false } = {}) => {
    if (data) setRefreshing(true);
    else setLoading(true);

    setError(null);
    try {
      const [host, instances] = await Promise.all([getHostDetail(hostId), getHostInstances(hostId)]);
      setData({ host, instances });
      if (showRefreshFeedback) {
        setFeedback({ type: 'success', message: 'Detalhes do host atualizados.' });
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
  }, [hostId]);

  useHeaderRefresh(() => loadData({ showRefreshFeedback: true }), refreshing || saving);

  function startEditName() {
    setNameInput(data?.host?.display_name || '');
    setEditingName(true);
  }

  async function saveName() {
    setNameSaving(true);
    try {
      const updated = await updateHost(hostId, { display_name: nameInput.trim() || null });
      setData((prev) => ({ ...prev, host: updated }));
      setEditingName(false);
      setFeedback({ type: 'success', message: 'Nome atualizado.' });
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Erro ao salvar nome' });
    } finally {
      setNameSaving(false);
    }
  }

  const columns = useMemo(
    () => [
      {
        key: 'automation_name',
        header: 'Automacao',
        render: (instance) => (
          <Link className="font-semibold text-app-accent hover:underline" to={`/automations/${instance.automation_id}/runs`}>
            {instance.automation_name}
          </Link>
        ),
      },
      { key: 'client_name', header: 'Cliente', render: (instance) => instance.client_name || 'N/D' },
      { key: 'root_folder', header: 'Pasta', render: (instance) => instance.root_folder || 'N/D' },
      { key: 'deployment_tag', header: 'Deployment', render: (instance) => instance.deployment_tag || 'N/D' },
      { key: 'runs_count', header: 'Execucoes' },
      {
        key: 'last_run_started_at',
        header: 'Ultimo run',
        render: (instance) => formatDateTime(instance.last_run_started_at),
      },
      {
        key: 'actions',
        header: 'Acoes',
        render: (instance) => (
          <Link className="text-app-accent hover:underline" to={`/instances/${instance.instance_id}/runs`}>
            Ver runs
          </Link>
        ),
      },
    ],
    []
  );

  if (loading && !data) {
    return <LoadingState label="Carregando diagnostico da maquina..." />;
  }

  if (error && !data) {
    return (
      <ErrorState
        title={error.title || 'Falha no host'}
        message={getErrorMessage(error)}
        onRetry={() => loadData()}
        busy={refreshing}
      />
    );
  }

  return (
    <>
      <div className="mb-4 flex items-start justify-between gap-4">
        <div>
          {editingName ? (
            <div className="flex items-center gap-2">
              <input
                autoFocus
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') saveName(); if (e.key === 'Escape') setEditingName(false); }}
                placeholder={data?.host?.hostname || 'Nome amigavel'}
                className="rounded-xl border border-app-border bg-app-surface px-3 py-1.5 text-lg font-bold text-app-text outline-none focus:border-app-accent"
              />
              <button type="button" onClick={saveName} disabled={nameSaving} className="rounded-lg p-1.5 text-emerald-500 hover:bg-emerald-500/10 transition disabled:opacity-50">
                <Check className="h-4 w-4" />
              </button>
              <button type="button" onClick={() => setEditingName(false)} className="rounded-lg p-1.5 text-app-muted hover:bg-app-primary/10 transition">
                <X className="h-4 w-4" />
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold text-app-text">
                {data?.host?.display_name || data?.host?.hostname || 'Host sem nome'}
              </h1>
              <button type="button" onClick={startEditName} title="Renomear" className="rounded-lg p-1 text-app-muted hover:bg-app-primary/10 hover:text-app-text transition">
                <Pencil className="h-3.5 w-3.5" />
              </button>
            </div>
          )}
          <p className="text-xs text-app-muted mt-0.5">
            {data?.host?.display_name && data?.host?.hostname ? `${data.host.hostname} · ` : ''}
            {data?.host?.root_folder || 'Sem pasta raiz definida'}
          </p>
        </div>
        <Link
          to="/hosts"
          className="inline-flex items-center gap-2 rounded-xl border border-app-border px-3 py-2 text-sm text-app-muted transition hover:bg-app-primary/10"
        >
          <ArrowLeft className="h-4 w-4" /> Voltar
        </Link>
      </div>

      {error ? (
        <div className="mb-4">
          <ErrorState title={error.title || 'Falha parcial'} message={getErrorMessage(error)} onRetry={() => loadData()} />
        </div>
      ) : null}

      <section className="mb-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="IP" value={data?.host?.ip_address || 'N/D'} />
        <MetricCard label="Ambiente" value={data?.host?.environment || 'N/D'} />
        <MetricCard label="Robos alocados" value={data?.instances?.length || 0} />
        <MetricCard label="Ultima atividade" value={formatDateTime(data?.host?.last_seen_at)} />
      </section>

      <SectionCard
        title="Relacao de robos na maquina"
        subtitle="Automações vinculadas em todas as pastas registradas para esta maquina"
      >
        {data?.instances?.length ? (
          <DataTable columns={columns} rows={data.instances} rowKey={(row) => `${row.instance_id}-${row.automation_id}`} />
        ) : (
          <EmptyState title="Sem automacoes vinculadas" message="Este host ainda nao possui instancias registradas." />
        )}
      </SectionCard>

      <FeedbackToast type={feedback?.type} message={feedback?.message} onClose={() => setFeedback(null)} />
    </>
  );
}

export default HostDetailPage;
