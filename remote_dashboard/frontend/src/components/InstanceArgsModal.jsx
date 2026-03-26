import { Hash, Plus, Save, Sliders, Trash2, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { updateInstanceArgs } from '../lib/api';
import BusyButton from './BusyButton';
import FeedbackToast from './FeedbackToast';

const ARG_TYPES = [
  { value: 'named', label: 'Nomeado', hint: '--flag valor' },
  { value: 'flag', label: 'Flag (bool)', hint: '--verbose' },
  { value: 'positional', label: 'Posicional', hint: 'sys.argv[N]' },
];

function emptyArg() {
  return { name: '', description: '', type: 'named', values: [], position: 1 };
}

function ValuesEditor({ values, onChange }) {
  const [input, setInput] = useState('');

  function addValue() {
    const v = input.trim();
    if (!v || values.includes(v)) return;
    onChange([...values, v]);
    setInput('');
  }

  return (
    <div className="mt-1">
      <div className="flex flex-wrap gap-1 mb-1">
        {values.map((v) => (
          <span
            key={v}
            className="inline-flex items-center gap-1 rounded-md bg-app-primary/10 px-2 py-0.5 text-[10px] font-mono font-semibold text-app-accent"
          >
            {v}
            <button
              type="button"
              onClick={() => onChange(values.filter((x) => x !== v))}
              className="text-app-muted hover:text-rose-500"
            >
              <X className="h-2.5 w-2.5" />
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-1.5">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); addValue(); } }}
          placeholder="Adicionar valor..."
          className="flex-1 text-xs"
        />
        <button
          type="button"
          onClick={addValue}
          className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-app-border bg-app-surface text-app-muted hover:border-app-accent/40 hover:text-app-accent"
        >
          <Plus className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}

function ArgRow({ arg, index, total, onChange, onRemove }) {
  return (
    <div className="rounded-xl border border-app-border bg-app-elevated/40 p-3 space-y-2.5">
      <div className="flex items-start gap-2">
        {/* Type selector */}
        <div className="w-36 shrink-0">
          <label className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-app-muted">Tipo</label>
          <select
            value={arg.type}
            onChange={(e) => onChange({ ...arg, type: e.target.value })}
            className="w-full text-xs"
          >
            {ARG_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
          <span className="text-[9px] font-mono text-app-muted/70 mt-0.5 block">
            ex: {ARG_TYPES.find((t) => t.value === arg.type)?.hint}
          </span>
        </div>

        {/* Name */}
        <div className="flex-1 min-w-0">
          <label className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-app-muted">
            {arg.type === 'positional' ? 'Rotulo' : 'Nome do Argumento'}
          </label>
          <input
            type="text"
            value={arg.name}
            onChange={(e) => onChange({ ...arg, name: e.target.value })}
            placeholder={arg.type === 'positional' ? 'ex: modo' : 'ex: --stages'}
            className="w-full text-xs font-mono"
          />
        </div>

        {/* Position (positional only) */}
        {arg.type === 'positional' && (
          <div className="w-20 shrink-0">
            <label className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-app-muted">Posicao</label>
            <input
              type="number"
              min={1}
              value={arg.position || 1}
              onChange={(e) => onChange({ ...arg, position: Number(e.target.value) })}
              className="w-full text-xs"
            />
          </div>
        )}

        {/* Remove */}
        <button
          type="button"
          onClick={onRemove}
          className="mt-6 inline-flex h-7 w-7 items-center justify-center rounded-lg border border-app-border text-app-muted transition hover:border-rose-400 hover:text-rose-500"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Description */}
      <div>
        <label className="mb-1 block text-[10px] font-bold uppercase tracking-wider text-app-muted">Descricao</label>
        <input
          type="text"
          value={arg.description || ''}
          onChange={(e) => onChange({ ...arg, description: e.target.value })}
          placeholder="O que este argumento faz..."
          className="w-full text-xs"
        />
      </div>

      {/* Values (not for plain flags) */}
      {arg.type !== 'flag' && (
        <div>
          <label className="mb-0.5 block text-[10px] font-bold uppercase tracking-wider text-app-muted">
            Valores Permitidos <span className="font-normal normal-case text-app-muted/70">(opcional — se vazio, texto livre)</span>
          </label>
          <ValuesEditor
            values={arg.values || []}
            onChange={(v) => onChange({ ...arg, values: v })}
          />
        </div>
      )}
    </div>
  );
}

function InstanceArgsModal({ instance, onClose, onSaved }) {
  const [args, setArgs] = useState([]);
  const [saving, setSaving] = useState(false);
  const [feedback, setFeedback] = useState(null);

  useEffect(() => {
    // Normalise stored args: ensure all fields present
    const raw = Array.isArray(instance?.available_args) ? instance.available_args : [];
    setArgs(
      raw.map((a) => ({
        name: a.name || '',
        description: a.description || '',
        type: a.type || (a.values?.length ? 'named' : 'named'),
        values: a.values || [],
        position: a.position || 1,
      }))
    );
  }, [instance]);

  function addArg() {
    setArgs((prev) => [...prev, emptyArg()]);
  }

  function updateArg(index, updated) {
    setArgs((prev) => prev.map((a, i) => (i === index ? updated : a)));
  }

  function removeArg(index) {
    setArgs((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSave() {
    const cleaned = args
      .filter((a) => a.name.trim())
      .map((a) => {
        const out = { name: a.name.trim(), type: a.type };
        if (a.description.trim()) out.description = a.description.trim();
        if (a.values?.length) out.values = a.values;
        if (a.type === 'positional') out.position = a.position;
        return out;
      });

    setSaving(true);
    try {
      await updateInstanceArgs(instance.id, { available_args: cleaned });
      setFeedback({ type: 'success', message: 'Argumentos salvos!' });
      setTimeout(() => {
        onSaved?.();
        onClose();
      }, 700);
    } catch (err) {
      setFeedback({ type: 'error', message: err.message || 'Erro ao salvar.' });
    } finally {
      setSaving(false);
    }
  }

  const instanceLabel = [
    instance?.host_hostname,
    instance?.client_name,
    instance?.deployment_tag,
  ]
    .filter(Boolean)
    .join(' · ');

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 backdrop-blur-sm">
      <div className="relative flex max-h-[90vh] w-full max-w-2xl flex-col rounded-2xl border border-app-border bg-app-surface shadow-2xl animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-app-border/40 px-6 py-4">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#2b114a] text-white">
              <Sliders className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-app-text">Argumentos da Instancia</h2>
              {instanceLabel && (
                <p className="text-xs text-app-muted">{instanceLabel}</p>
              )}
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

        {/* Info banner */}
        <div className="mx-6 mt-4 rounded-lg border border-app-border/60 bg-app-elevated/60 px-3 py-2 text-[10px] text-app-muted leading-relaxed">
          Cadastre os argumentos que o robô aceita. Ao executar via dashboard, eles aparecerao como controles ao inves de texto livre.
          Os argumentos também podem ser detectados automaticamente via <code className="font-mono">available_args</code> no <code className="font-mono">logger_config.json</code>.
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto custom-scrollbar px-6 py-4 space-y-3">
          {args.length === 0 && (
            <div className="rounded-xl border border-dashed border-app-border bg-app-elevated/30 px-6 py-8 text-center">
              <Hash className="mx-auto mb-2 h-8 w-8 text-app-muted/40" />
              <p className="text-sm font-semibold text-app-muted">Nenhum argumento cadastrado</p>
              <p className="mt-1 text-xs text-app-muted/70">
                Clique em "Adicionar Argumento" para comecar.
              </p>
            </div>
          )}

          {args.map((arg, i) => (
            <ArgRow
              key={i}
              arg={arg}
              index={i}
              total={args.length}
              onChange={(updated) => updateArg(i, updated)}
              onRemove={() => removeArg(i)}
            />
          ))}

          <button
            type="button"
            onClick={addArg}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-dashed border-app-border bg-app-surface py-2.5 text-xs font-semibold text-app-muted transition hover:border-app-accent/40 hover:text-app-accent"
          >
            <Plus className="h-4 w-4" /> Adicionar Argumento
          </button>
        </div>

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
            onClick={handleSave}
            className="inline-flex items-center gap-2 rounded-xl bg-[#2b114a] px-5 py-2.5 text-xs font-bold text-white shadow hover:bg-[#6d558d]"
          >
            <Save className="h-3.5 w-3.5" /> Salvar Argumentos
          </BusyButton>
        </div>

        <FeedbackToast type={feedback?.type} message={feedback?.message} onDone={() => setFeedback(null)} />
      </div>
    </div>
  );
}

export default InstanceArgsModal;
