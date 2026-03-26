import { ArrowLeft } from 'lucide-react';
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
import { getClientAutomations, getClientDetail } from '../lib/api';
import { formatDateTime, getErrorMessage } from '../lib/format';
import useHeaderRefresh from '../layout/useHeaderRefresh';

function ClientDetailPage() {
  const { clientId } = useParams();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const [data, setData] = useState(null);
  const [feedback, setFeedback] = useState(null);

  const loadData = async ({ showRefreshFeedback = false } = {}) => {
    if (data) setRefreshing(true);
    else setLoading(true);

    setError(null);
    try {
      const [client, automations] = await Promise.all([
        getClientDetail(clientId),
        getClientAutomations(clientId),
      ]);
      setData({ client, automations });
      if (showRefreshFeedback) {
        setFeedback({ type: 'success', message: 'Detalhes do cliente atualizados.' });
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
  }, [clientId]);

  useHeaderRefresh(() => loadData({ showRefreshFeedback: true }), refreshing || saving);

  const columns = useMemo(
    () => [
      {
        key: 'automation_name',
        header: 'Automacao',
        render: (automation) => (
          <Link className="font-semibold text-app-accent hover:underline" to={`/automations/${automation.automation_id}/runs`}>
            {automation.automation_name}
          </Link>
        ),
      },
      { key: 'host_hostname', header: 'Host', render: (automation) => automation.host_display_name || automation.host_hostname || 'N/D' },
      { key: 'host_ip', header: 'IP', render: (automation) => automation.host_ip || '-' },
      { key: 'deployment_tag', header: 'Deployment', render: (automation) => automation.deployment_tag || 'N/D' },
      {
        key: 'last_run_started_at',
        header: 'Ultimo run',
        render: (automation) => formatDateTime(automation.last_run_started_at),
      },
      { key: 'total_runs', header: 'Execucoes' },
    ],
    []
  );

  if (loading && !data) {
    return <LoadingState label="Carregando detalhes do cliente..." />;
  }

  if (error && !data) {
    return (
      <ErrorState
        title={error.title || 'Falha no cliente'}
        message={getErrorMessage(error)}
        onRetry={() => loadData()}
        busy={refreshing}
      />
    );
  }

  return (
    <>
      <PageHeader
        title={data?.client?.name || 'Cliente'}
        subtitle={data?.client?.contact_email || 'Sem contato principal'}
        actions={[
          <Link
            key="back-clients"
            to="/clients"
            className="inline-flex items-center gap-2 rounded-xl border border-app-border px-3 py-2 text-sm text-app-muted transition hover:bg-app-primary/10"
          >
            <ArrowLeft className="h-4 w-4" /> Voltar
          </Link>,
        ]}
      />

      {error ? (
        <div className="mb-4">
          <ErrorState title={error.title || 'Falha parcial'} message={getErrorMessage(error)} onRetry={() => loadData()} />
        </div>
      ) : null}

      <section className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Codigo" value={data?.client?.external_code || 'N/D'} />
        <MetricCard label="Robos ativos" value={data?.client?.automations_count || 0} />
        <MetricCard label="Instancias" value={data?.client?.instances_count || 0} />
        <MetricCard label="Ultima atividade" value={formatDateTime(data?.client?.last_seen_at)} />
      </section>

      <SectionCard title="Relacao de automacoes do cliente" subtitle="Host, deployment e volume de execucoes">
        {data?.automations?.length ? (
          <DataTable
            columns={columns}
            rows={data.automations}
            rowKey={(row) => `${row.automation_id}-${row.host_id || 'hostless'}-${row.deployment_tag || 'none'}`}
          />
        ) : (
          <EmptyState title="Sem automacoes vinculadas" message="Nao ha relacoes de automacao para este cliente." />
        )}
      </SectionCard>

      <FeedbackToast type={feedback?.type} message={feedback?.message} onClose={() => setFeedback(null)} />
    </>
  );
}

export default ClientDetailPage;
