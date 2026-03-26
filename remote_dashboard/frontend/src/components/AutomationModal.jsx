import { Cpu, X, RefreshCw, Box, Users, Sliders } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import BusyButton from './BusyButton';
import DataTable from './DataTable';
import EmptyState from './EmptyState';
import ErrorState from './ErrorState';
import InstanceArgsModal from './InstanceArgsModal';
import LoadingState from './LoadingState';
import { getAutomationDetail, getAutomationInstances } from '../lib/api';
import { formatDateTime, getErrorMessage } from '../lib/format';

function AutomationModal({ automationId, onClose }) {
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);
    const [error, setError] = useState(null);
    const [data, setData] = useState(null);
    const [argsInstance, setArgsInstance] = useState(null);

    const loadData = async () => {
        if (data) setRefreshing(true);
        else setLoading(true);

        setError(null);
        try {
            const [automation, instances] = await Promise.all([
                getAutomationDetail(automationId),
                getAutomationInstances(automationId),
            ]);
            setData({ automation, instances });
        } catch (requestError) {
            setError(requestError);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    useEffect(() => {
        if (automationId) {
            loadData();
        }
    }, [automationId]);

    // Handle ESC key to close
    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [onClose]);

    if (!automationId) return null;

    const columns = [
        { key: 'client_name', header: 'Cliente', render: (instance) => instance.client_name || 'N/D' },
        { key: 'host_hostname', header: 'Host', render: (instance) => instance.host_display_name || instance.host_hostname || 'N/D' },
        { key: 'host_ip', header: 'IP', render: (instance) => instance.host_ip || 'N/D' },
        { key: 'deployment_tag', header: 'Deployment', render: (instance) => instance.deployment_tag || 'N/D' },
        { key: 'total_runs', header: 'Execucoes' },
        {
            key: 'last_run_started_at',
            header: 'Ultimo run',
            render: (instance) => formatDateTime(instance.last_run_started_at),
        },
        {
            key: 'available_args',
            header: 'Args',
            render: (instance) => {
                const count = instance.available_args?.length || 0;
                return (
                    <button
                        type="button"
                        onClick={() => setArgsInstance(instance)}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-app-border px-2.5 py-1 text-[10px] font-semibold text-app-muted transition hover:border-app-accent/40 hover:text-app-accent"
                        title="Gerenciar argumentos"
                    >
                        <Sliders className="h-3 w-3" />
                        {count > 0 ? `${count} arg${count !== 1 ? 's' : ''}` : 'Gerenciar'}
                    </button>
                );
            },
        },
        {
            key: 'actions',
            header: '',
            render: (instance) => (
                <Link className="text-app-accent hover:underline flex items-center justify-end" to={`/instances/${instance.id}/runs`}>
                    Ver runs
                </Link>
            ),
        },
    ];

    return (
        <>
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm transition-opacity animate-in fade-in duration-300"
            onClick={onClose}
        >
            <div
                className="relative flex max-h-[90vh] w-full max-w-5xl flex-col rounded-2xl border border-app-border bg-app-surface shadow-2xl animate-in zoom-in-95 duration-200"
                role="dialog"
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex-1 overflow-y-auto p-6 lg:p-10 custom-scrollbar">
                    {loading && !data ? (
                        <div className="py-20 text-center">
                            <LoadingState label="Inspecionando dados do robô..." />
                        </div>
                    ) : error && !data ? (
                        <div className="py-10">
                            <ErrorState
                                title={error.title || 'Falha ao carregar automação'}
                                message={getErrorMessage(error)}
                                onRetry={loadData}
                                busy={refreshing}
                            />
                        </div>
                    ) : (
                        <>
                            {/* Modal Header */}
                            <div className="flex flex-col md:flex-row md:items-start justify-between gap-6 border-b border-app-border/40 pb-6">
                                <div className="flex gap-5">
                                    <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-2xl border border-app-primary/10 bg-app-primary/5 text-[#6d558d]">
                                        <Cpu className="h-8 w-8" />
                                    </div>
                                    <div>
                                        <h2 className="text-2xl font-bold tracking-tight text-[#2b114a] mb-2">
                                            {data?.automation?.name || 'Automação'}
                                        </h2>
                                        <div className="flex flex-wrap items-center gap-3 text-sm text-[#2b114a]">
                                            <span className="font-mono text-xs font-bold bg-[#6d558d]/10 text-[#6d558d] px-2.5 py-1 rounded-lg">#{data?.automation?.code || '-'}</span>
                                            <span className="opacity-30">|</span>
                                            <span className="flex items-center gap-1.5 font-medium">
                                                <Users className="h-3.5 w-3.5 text-[#6d558d]" />
                                                Equipe: <span className="text-[#6d558d]">{data?.automation?.owner_team || 'N/D'}</span>
                                            </span>
                                        </div>
                                        {data?.automation?.description && (
                                            <p className="mt-4 text-[13px] text-[#6d558d] max-w-3xl leading-relaxed">
                                                {data.automation.description}
                                            </p>
                                        )}
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 mt-4 md:mt-0">
                                    <BusyButton
                                        busy={refreshing}
                                        onClick={loadData}
                                        className="inline-flex items-center gap-2 rounded-xl border border-app-border bg-transparent px-4 py-2 text-xs font-bold text-[#6d558d] transition hover:bg-[#6d558d]/10 hover:text-white"
                                    >
                                        <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} /> Atualizar
                                    </BusyButton>
                                    <Link
                                        to={`/automations/${automationId}/runs`}
                                        className="inline-flex items-center gap-2 rounded-xl bg-[#2b114a] px-5 py-2 text-xs font-bold text-white shadow transition hover:bg-[#6d558d]"
                                    >
                                        Histórico de Execuções
                                    </Link>
                                    <button
                                        onClick={onClose}
                                        className="p-2 ml-1 text-[#6d558d] hover:text-[#2b114a] transition rounded-full hover:bg-white/5 bg-transparent"
                                        aria-label="Fechar"
                                    >
                                        <X className="h-5 w-5" />
                                    </button>
                                </div>
                            </div>

                            {/* Fast Metrics Row */}
                            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 py-8">
                                <div className="flex flex-col border-l-2 border-[#2b114a]/30 pl-4">
                                    <span className="text-xs uppercase tracking-wider text-[#2b114a] font-bold mb-1">Instâncias Ativas</span>
                                    <span className="text-2xl font-bold text-[#6d558d] tracking-tight">{data?.automation?.instances_count || 0}</span>
                                </div>
                                <div className="flex flex-col border-l-2 border-[#2b114a]/30 pl-4">
                                    <span className="text-xs uppercase tracking-wider text-[#2b114a] font-bold mb-1">Hosts Distintos</span>
                                    <span className="text-2xl font-bold text-[#6d558d] tracking-tight">{data?.automation?.hosts_count || 0}</span>
                                </div>
                                <div className="flex flex-col border-l-2 border-[#2b114a]/30 pl-4">
                                    <span className="text-xs uppercase tracking-wider text-[#2b114a] font-bold mb-1">Clientes Atendidos</span>
                                    <span className="text-2xl font-bold text-[#6d558d] tracking-tight">{data?.automation?.clients_count || 0}</span>
                                </div>
                                <div className="flex flex-col border-l-2 border-[#2b114a]/30 pl-4">
                                    <span className="text-xs uppercase tracking-wider text-[#2b114a] font-bold mb-1">Momento do Último Run</span>
                                    <span className="text-sm font-medium text-[#6d558d] tracking-tight leading-[1.3] truncate" title={formatDateTime(data?.automation?.last_run_started_at)}>
                                        {data?.automation?.last_run_started_at ? formatDateTime(data.automation.last_run_started_at).replace(', ', '\n') : 'Sem registros'}
                                    </span>
                                </div>
                            </div>

                            {error && (
                                <div className="mb-6 rounded-xl bg-rose-500/5 border border-rose-500/20 p-4 text-xs text-rose-400 flex items-center gap-3">
                                    <div className="h-2 w-2 rounded-full bg-rose-500 animate-pulse" />
                                    <p><span className="font-bold">Aviso:</span> {getErrorMessage(error)}</p>
                                </div>
                            )}

                            {/* Instances Table */}
                            <div className="mt-4 rounded-xl border border-app-border bg-app-elevated/50 overflow-hidden shadow-sm">
                                <div className="flex items-center gap-2 border-b border-app-border/40 bg-app-elevated/80 px-5 py-3">
                                    <Box className="h-4 w-4 text-[#2b114a]" />
                                    <h3 className="text-sm font-semibold text-[#2b114a]">Relacão de Instâncias Implantadas</h3>
                                </div>
                                <div className="p-1 overflow-x-auto">
                                    {data?.instances?.length ? (
                                        <DataTable
                                            columns={columns.map(c => ({
                                                ...c,
                                                headerClassName: "!text-[#2b114a]",
                                                cellClassName: "!text-[#6d558d]",
                                            }))}
                                            rows={data.instances}
                                            rowKey={(row) => row.id}
                                        />
                                    ) : (
                                        <div className="py-12 text-center">
                                            <EmptyState title="Nenhuma instância ativa" message="Este robô ainda não foi implantado em nenhum cliente ou servidor." />
                                        </div>
                                    )}
                                </div>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>

        {argsInstance && (
            <InstanceArgsModal
                instance={argsInstance}
                onClose={() => setArgsInstance(null)}
                onSaved={() => { setArgsInstance(null); loadData(); }}
            />
        )}
        </>
    );
}

export default AutomationModal;
