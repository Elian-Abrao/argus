import { Calendar, Play, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { getAutomationInstances, getAutomations, getAgentStatus, createSchedule, runNow } from '../lib/api';
import BusyButton from './BusyButton';
import FeedbackToast from './FeedbackToast';

const RECURRENCE_OPTIONS = [
  { value: 'daily', label: 'Diario' },
  { value: 'weekdays', label: 'Dias uteis (Seg-Sex)' },
  { value: 'specific_days', label: 'Dias especificos' },
  { value: 'monthly', label: 'Mensal' },
  { value: 'yearly', label: 'Anual' },
];

const DAY_LABELS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'];

function ScheduleModal({ mode = 'schedule', onClose, onCreated }) {
  const isRunNow = mode === 'run-now';

  const [automations, setAutomations] = useState([]);
  const [allInstances, setAllInstances] = useState([]);   // todas as instâncias da automação selecionada
  const [connectedHostIds, setConnectedHostIds] = useState(new Set());
  const [loadingInstances, setLoadingInstances] = useState(false);
  const [loading, setLoading] = useState(true);
  const [argValues, setArgValues] = useState({});  // argName → value (string) or '' for flags
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  const [selectedAutomation, setSelectedAutomation] = useState('');
  const [selectedClient, setSelectedClient] = useState('');
  const [selectedHost, setSelectedHost] = useState('');    // host_id da instância escolhida
  const [selectedInstance, setSelectedInstance] = useState('');
  const [script, setScript] = useState('main.py');
  const [args, setArgs] = useState('');
  const [executionMode, setExecutionMode] = useState('parallel');
  const [recurrenceType, setRecurrenceType] = useState('daily');
  const [time, setTime] = useState('08:00');
  const [daysOfWeek, setDaysOfWeek] = useState([]);
  const [dayOfMonth, setDayOfMonth] = useState(1);
  const [businessDay, setBusinessDay] = useState(false);
  const [yearMonth, setYearMonth] = useState(1);
  const [enabled, setEnabled] = useState(true);

  // Carrega automações e status dos agentes no início
  useEffect(() => {
    async function load() {
      try {
        const [automRes, statusRes] = await Promise.all([
          getAutomations({ limit: 200 }),
          getAgentStatus().catch(() => null),
        ]);
        setAutomations(automRes.items || []);

        if (statusRes?.items) {
          const connected = new Set(
            statusRes.items.filter((h) => h.connected).map((h) => h.host_id)
          );
          setConnectedHostIds(connected);
        }
      } catch {
        // silent
      } finally {
        setLoading(false);
      }
    }
    load();
  }, []);

  // Ao selecionar automação, carrega todas as suas instâncias
  useEffect(() => {
    if (!selectedAutomation) {
      setAllInstances([]);
      setSelectedClient('');
      setSelectedHost('');
      setSelectedInstance('');
      return;
    }
    async function loadInstances() {
      setLoadingInstances(true);
      try {
        const res = await getAutomationInstances(selectedAutomation);
        const items = res.items || res || [];
        setAllInstances(items);

        // Filtra para instâncias em hosts conectados
        const visible = connectedHostIds.size > 0
          ? items.filter((i) => i.host_id && connectedHostIds.has(i.host_id))
          : items;
        const effective = visible.length > 0 ? visible : items;

        // Auto-seleciona cliente se só houver 1
        const uniqueClients = [...new Map(effective.filter(i => i.client_id).map(i => [i.client_id, i])).values()];
        if (uniqueClients.length === 1) {
          setSelectedClient(uniqueClients[0].client_id);
        } else {
          setSelectedClient('');
          setSelectedHost('');
          setSelectedInstance('');
        }
      } catch {
        setAllInstances([]);
      } finally {
        setLoadingInstances(false);
      }
    }
    loadInstances();
  }, [selectedAutomation]);

  // Apenas instâncias em hosts com agente conectado (ou todas se nenhum estiver conectado)
  const connectedInstances = useMemo(() => {
    if (connectedHostIds.size === 0) return allInstances;
    const filtered = allInstances.filter((i) => i.host_id && connectedHostIds.has(i.host_id));
    return filtered.length > 0 ? filtered : allInstances;
  }, [allInstances, connectedHostIds]);

  // Clientes disponíveis para a automação selecionada
  const availableClients = useMemo(() => {
    const map = new Map();
    connectedInstances.forEach(i => {
      if (i.client_id && !map.has(i.client_id)) {
        map.set(i.client_id, { id: i.client_id, name: i.client_name || i.client_id });
      }
    });
    return [...map.values()];
  }, [connectedInstances]);

  // Instâncias filtradas pelo cliente selecionado (dentro das conectadas)
  const instancesByClient = useMemo(() => {
    if (!selectedClient) return connectedInstances;
    return connectedInstances.filter(i => i.client_id === selectedClient);
  }, [connectedInstances, selectedClient]);

  // Hosts disponíveis para o cliente selecionado
  const availableHosts = useMemo(() => {
    const map = new Map();
    instancesByClient.forEach(i => {
      if (i.host_id && !map.has(i.host_id)) {
        map.set(i.host_id, {
          id: i.host_id,
          label: i.host_display_name || i.host_hostname || i.host_ip || i.host_id,
        });
      }
    });
    return [...map.values()];
  }, [instancesByClient]);

  // Ao mudar cliente, auto-seleciona host/instância se só houver 1
  useEffect(() => {
    if (!selectedClient) return;
    setSelectedHost('');
    setSelectedInstance('');
    if (availableHosts.length === 1) {
      setSelectedHost(availableHosts[0].id);
    }
  }, [selectedClient]);

  // Ao mudar host, resolve a instância exata
  useEffect(() => {
    if (!selectedHost) {
      setSelectedInstance('');
      setArgValues({});
      return;
    }
    const match = instancesByClient.find(i => i.host_id === selectedHost);
    setSelectedInstance(match ? match.id : '');
    setArgValues({});
  }, [selectedHost, instancesByClient]);

  // Instância resolvida com seus dados (including available_args)
  const resolvedInstance = useMemo(() => {
    if (!selectedInstance) return null;
    return instancesByClient.find(i => i.id === selectedInstance) || null;
  }, [selectedInstance, instancesByClient]);

  const availableArgs = resolvedInstance?.available_args || [];

  const filteredAutomations = automations;

  function toggleDay(day) {
    setDaysOfWeek((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day].sort()
    );
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!selectedInstance) {
      setFeedback({ type: 'error', message: 'Selecione uma instancia de automacao.' });
      return;
    }

    setSaving(true);
    setFeedback(null);

    try {
      let parsedArgs;
      if (availableArgs.length > 0) {
        // Positional args come first, sorted by position; named/flags follow
        const positional = availableArgs
          .filter((a) => a.type === 'positional')
          .sort((a, b) => (a.position || 1) - (b.position || 1));
        const named = availableArgs.filter((a) => a.type !== 'positional');

        parsedArgs = [];

        // Positional: add value directly (no flag name)
        positional.forEach((argDef) => {
          const val = argValues[argDef.name];
          if (val && val !== false && val !== true) parsedArgs.push(String(val));
        });

        // Named / flags
        named.forEach((argDef) => {
          const val = argValues[argDef.name];
          if (val === undefined || val === null || val === '' || val === false) return;
          parsedArgs.push(argDef.name);
          if (val !== true) parsedArgs.push(String(val));
        });
      } else {
        parsedArgs = args.trim() ? args.split(/\s+/) : [];
      }

      if (isRunNow) {
        await runNow({
          automation_instance_id: selectedInstance,
          script,
          args: parsedArgs,
          execution_mode: executionMode,
        });
        setFeedback({ type: 'success', message: 'Comando enviado com sucesso!' });
      } else {
        const recurrenceConfig = { time };
        if (recurrenceType === 'specific_days') {
          recurrenceConfig.days_of_week = daysOfWeek;
        }
        if (recurrenceType === 'monthly') {
          recurrenceConfig.day_of_month = dayOfMonth;
          recurrenceConfig.business_day = businessDay;
        }
        if (recurrenceType === 'yearly') {
          recurrenceConfig.month = yearMonth;
          recurrenceConfig.day_of_month = dayOfMonth;
        }

        await createSchedule({
          automation_instance_id: selectedInstance,
          script,
          args: parsedArgs,
          recurrence_type: recurrenceType,
          recurrence_config: recurrenceConfig,
          execution_mode: executionMode,
          enabled,
        });
        setFeedback({ type: 'success', message: 'Agendamento criado com sucesso!' });
      }

      setTimeout(() => {
        onCreated?.();
        onClose();
      }, 800);
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Erro ao salvar.' });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative flex max-h-[90vh] w-full max-w-2xl flex-col rounded-2xl border border-app-border bg-app-surface shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-app-border/40 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#2b114a] text-white">
              {isRunNow ? <Play className="h-5 w-5" /> : <Calendar className="h-5 w-5" />}
            </div>
            <div>
              <h2 className="text-lg font-bold text-app-text">
                {isRunNow ? 'Iniciar Agora' : 'Novo Agendamento'}
              </h2>
              <p className="text-xs text-app-muted">
                {isRunNow ? 'Execucao imediata de automacao' : 'Configurar execucao recorrente'}
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-2 text-app-muted hover:bg-app-primary/10 hover:text-app-text"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Body */}
        <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto custom-scrollbar px-6 py-5 space-y-5">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="h-8 w-8 animate-spin rounded-full border-2 border-app-primary border-t-transparent" />
            </div>
          ) : (
            <>
              {/* Automation Selector */}
              <div>
                <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-app-muted">Automacao</label>
                <select
                  value={selectedAutomation}
                  onChange={(e) => setSelectedAutomation(e.target.value)}
                  className="w-full"
                >
                  <option value="">Selecione uma automacao</option>
                  {filteredAutomations.map((a) => (
                    <option key={a.id} value={a.id}>{a.name} ({a.code})</option>
                  ))}
                </select>
              </div>

              {/* Loading instâncias */}
              {loadingInstances && (
                <div className="flex items-center gap-2 text-xs text-app-muted">
                  <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-app-primary border-t-transparent" />
                  Carregando instancias...
                </div>
              )}

              {/* Aviso se a automação não tem instâncias em agentes conectados */}
              {!loadingInstances && selectedAutomation && allInstances.length > 0 && connectedInstances.length === 0 && (
                <div className="rounded-lg border border-amber-300/60 bg-amber-50 px-3 py-2 text-xs text-amber-800">
                  Nenhum agente conectado para esta automacao. O comando ficara pendente ate um agente conectar.
                </div>
              )}

              {/* Cliente — só aparece se houver mais de 1 */}
              {!loadingInstances && selectedAutomation && availableClients.length > 1 && (
                <div>
                  <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-app-muted">Cliente</label>
                  <select
                    value={selectedClient}
                    onChange={(e) => setSelectedClient(e.target.value)}
                    className="w-full"
                  >
                    <option value="">Selecione um cliente</option>
                    {availableClients.map((c) => (
                      <option key={c.id} value={c.id}>{c.name}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Cliente auto-selecionado — exibe como leitura */}
              {!loadingInstances && selectedAutomation && availableClients.length === 1 && (
                <div>
                  <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-app-muted">Cliente</label>
                  <div className="flex h-9 items-center rounded-lg border border-app-border bg-app-elevated px-3 text-sm text-app-muted">
                    {availableClients[0].name}
                  </div>
                </div>
              )}

              {/* Maquina — só aparece se houver mais de 1 */}
              {!loadingInstances && selectedClient && availableHosts.length > 1 && (
                <div>
                  <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-app-muted">Maquina</label>
                  <select
                    value={selectedHost}
                    onChange={(e) => setSelectedHost(e.target.value)}
                    className="w-full"
                  >
                    <option value="">Selecione uma maquina</option>
                    {availableHosts.map((h) => (
                      <option key={h.id} value={h.id}>{h.label}</option>
                    ))}
                  </select>
                </div>
              )}

              {/* Maquina auto-selecionada — exibe como leitura */}
              {!loadingInstances && selectedClient && availableHosts.length === 1 && (
                <div>
                  <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-app-muted">Maquina</label>
                  <div className="flex h-9 items-center rounded-lg border border-app-border bg-app-elevated px-3 text-sm text-app-muted">
                    {availableHosts[0].label}
                  </div>
                </div>
              )}

              {/* Script */}
              <div>
                <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-app-muted">Script</label>
                <input
                  type="text"
                  value={script}
                  onChange={(e) => setScript(e.target.value)}
                  placeholder="main.py"
                  className="w-full"
                />
              </div>

              {/* Argumentos — só aparece se a instância tiver available_args cadastrados */}
              {availableArgs.length > 0 && (
                <div>
                  <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-app-muted">Argumentos</label>
                  <div className="space-y-2 rounded-xl border border-app-border bg-app-elevated/40 p-3">
                    {[
                      // Positionals first (sorted by position), then named/flags
                      ...availableArgs.filter((a) => a.type === 'positional').sort((a, b) => (a.position || 1) - (b.position || 1)),
                      ...availableArgs.filter((a) => a.type !== 'positional'),
                    ].map((argDef) => {
                      const name = argDef.name;
                      const desc = argDef.description || '';
                      const allowed = argDef.values || [];
                      const isFlag = argDef.type === 'flag';
                      const isPositional = argDef.type === 'positional';
                      const val = argValues[name];

                      return (
                        <div key={name} className="flex items-start gap-3">
                          {/* Positionals are always shown (required), flags/named have checkbox */}
                          {isPositional ? (
                            <span className="mt-1.5 flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-app-primary/15 text-[8px] font-bold text-app-accent">
                              {argDef.position || 1}
                            </span>
                          ) : (
                            <input
                              type="checkbox"
                              id={`arg-${name}`}
                              checked={val !== undefined && val !== false}
                              onChange={(e) => {
                                setArgValues((prev) => {
                                  const next = { ...prev };
                                  if (e.target.checked) {
                                    // flags → true; com valores predefinidos → primeiro valor; livre → null (mostra input vazio)
                                    next[name] = isFlag ? true : (allowed[0] ?? null);
                                  } else {
                                    delete next[name];
                                  }
                                  return next;
                                });
                              }}
                              className="mt-0.5 rounded"
                            />
                          )}
                          <div className="flex-1 min-w-0">
                            <label
                              htmlFor={isPositional ? undefined : `arg-${name}`}
                              className={`block text-xs font-mono font-semibold text-app-text ${!isPositional ? 'cursor-pointer' : ''}`}
                            >
                              {isPositional ? (
                                <span className="text-app-muted">{name}</span>
                              ) : name}
                            </label>
                            {desc && <p className="text-[10px] text-app-muted leading-tight">{desc}</p>}
                            {/* Value input: sempre para posicionais; para named quando checked (val != undefined/false) */}
                            {(isPositional || (!isFlag && val !== undefined && val !== false)) && (
                              allowed.length > 0 ? (
                                <select
                                  value={typeof val === 'string' ? val : (allowed[0] || '')}
                                  onChange={(e) => setArgValues((prev) => ({ ...prev, [name]: e.target.value }))}
                                  className="mt-1 w-full text-xs"
                                >
                                  {!isPositional && <option value="">-- nenhum --</option>}
                                  {allowed.map((v) => (
                                    <option key={v} value={v}>{v}</option>
                                  ))}
                                </select>
                              ) : (
                                <input
                                  type="text"
                                  value={typeof val === 'string' ? val : ''}
                                  onChange={(e) => setArgValues((prev) => ({ ...prev, [name]: e.target.value }))}
                                  className="mt-1 w-full text-xs"
                                  placeholder={isPositional ? `sys.argv[${argDef.position || 1}]` : 'valor...'}
                                />
                              )
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Execution Mode */}
              <div>
                <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-app-muted">Modo de execucao</label>
                <div className="flex gap-2">
                  {['parallel', 'sequential'].map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setExecutionMode(m)}
                      className={`flex-1 rounded-xl border px-4 py-2.5 text-xs font-semibold uppercase tracking-wider transition ${
                        executionMode === m
                          ? 'border-app-accent bg-app-primary/15 text-app-accent'
                          : 'border-app-border bg-app-surface text-app-muted hover:border-app-primary/40'
                      }`}
                    >
                      {m === 'parallel' ? 'Paralelo' : 'Sequencial'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Recurrence (schedule mode only) */}
              {!isRunNow && (
                <>
                  <div className="border-t border-app-border/40 pt-5">
                    <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-app-muted">Recorrencia</label>
                    <select
                      value={recurrenceType}
                      onChange={(e) => setRecurrenceType(e.target.value)}
                      className="w-full"
                    >
                      {RECURRENCE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                  </div>

                  {/* Time */}
                  <div>
                    <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-app-muted">Horario</label>
                    <input
                      type="time"
                      value={time}
                      onChange={(e) => setTime(e.target.value)}
                      className="w-full"
                    />
                  </div>

                  {/* Specific Days */}
                  {recurrenceType === 'specific_days' && (
                    <div>
                      <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-app-muted">Dias da semana</label>
                      <div className="flex gap-2">
                        {DAY_LABELS.map((label, i) => (
                          <button
                            key={i}
                            type="button"
                            onClick={() => toggleDay(i)}
                            className={`h-10 w-10 rounded-lg text-xs font-semibold transition ${
                              daysOfWeek.includes(i)
                                ? 'bg-app-accent text-white'
                                : 'border border-app-border bg-app-surface text-app-muted hover:border-app-primary/40'
                            }`}
                          >
                            {label}
                          </button>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Monthly / Yearly */}
                  {(recurrenceType === 'monthly' || recurrenceType === 'yearly') && (
                    <div className="grid grid-cols-2 gap-4">
                      {recurrenceType === 'yearly' && (
                        <div>
                          <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-app-muted">Mes</label>
                          <select
                            value={yearMonth}
                            onChange={(e) => setYearMonth(Number(e.target.value))}
                            className="w-full"
                          >
                            {Array.from({ length: 12 }, (_, i) => (
                              <option key={i + 1} value={i + 1}>
                                {new Date(2024, i).toLocaleString('pt-BR', { month: 'long' })}
                              </option>
                            ))}
                          </select>
                        </div>
                      )}
                      <div>
                        <label className="mb-1.5 block text-xs font-semibold uppercase tracking-wider text-app-muted">Dia do mes</label>
                        <input
                          type="number"
                          min={1}
                          max={31}
                          value={dayOfMonth}
                          onChange={(e) => setDayOfMonth(Number(e.target.value))}
                          className="w-full"
                        />
                      </div>
                      {recurrenceType === 'monthly' && (
                        <div className="flex items-end gap-2">
                          <label className="flex items-center gap-2 text-xs text-app-muted">
                            <input
                              type="checkbox"
                              checked={businessDay}
                              onChange={(e) => setBusinessDay(e.target.checked)}
                              className="rounded"
                            />
                            Dia util
                          </label>
                        </div>
                      )}
                    </div>
                  )}

                  {/* Enabled */}
                  <div className="flex items-center gap-3">
                    <label className="flex items-center gap-2 text-sm text-app-text">
                      <input
                        type="checkbox"
                        checked={enabled}
                        onChange={(e) => setEnabled(e.target.checked)}
                        className="rounded"
                      />
                      Habilitado
                    </label>
                  </div>
                </>
              )}
            </>
          )}
        </form>

        {/* Footer */}
        <div className="flex items-center justify-end gap-3 border-t border-app-border/40 px-6 py-4">
          <button
            type="button"
            onClick={onClose}
            className="rounded-xl border border-app-border px-5 py-2.5 text-xs font-semibold text-app-muted hover:bg-app-primary/5"
          >
            Cancelar
          </button>
          <BusyButton
            busy={saving}
            onClick={handleSubmit}
            className="rounded-xl bg-[#2b114a] px-5 py-2.5 text-xs font-bold text-white shadow hover:bg-[#6d558d]"
          >
            {isRunNow ? 'Executar' : 'Criar Agendamento'}
          </BusyButton>
        </div>

        <FeedbackToast type={feedback?.type} message={feedback?.message} onDone={() => setFeedback(null)} />
      </div>
    </div>
  );
}

export default ScheduleModal;
