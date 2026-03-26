/**
 * ExecutionView — feed cronológico anotado.
 *
 * Os logs permanecem em ordem cronológica real.
 * O call_chain cria blocos visuais de contexto em volta dos logs.
 * Cada troca de call_chain = novo bloco, preservando o interleaving real.
 * Loops ficam visíveis porque o mesmo bloco reaparece múltiplas vezes.
 *
 * Fluxo: logs → buildContextBlocks() → render
 */
import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  GitBranch,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import { getRunLogs } from '../lib/api';

// ─── Helpers ──────────────────────────────────────────────────────────────────

const LEVEL_STYLE = {
  CRITICAL: 'bg-fuchsia-100 text-fuchsia-700 border-fuchsia-300',
  ERROR:    'bg-rose-100    text-rose-700    border-rose-300',
  WARNING:  'bg-amber-100   text-amber-700   border-amber-300',
  INFO:     'bg-emerald-100 text-emerald-700 border-emerald-200',
  DEBUG:    'bg-sky-100     text-sky-700     border-sky-200',
  SUCCESS:  'bg-green-100   text-green-700   border-green-200',
  SCREEN:   'bg-slate-100   text-slate-600   border-slate-200',
};

// Left border colors by call_chain depth
const DEPTH_BORDER_COLOR = [
  '#60a5fa', // blue-400    depth 1
  '#a78bfa', // violet-400  depth 2
  '#2dd4bf', // teal-400    depth 3
  '#fb923c', // orange-400  depth 4
  '#f472b6', // pink-400    depth 5+
];

function depthBorderColor(depth) {
  return DEPTH_BORDER_COLOR[Math.min(depth - 1, DEPTH_BORDER_COLOR.length - 1)];
}

function formatDuration(ms) {
  if (!ms || ms < 0) return null;
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.round((ms % 60_000) / 1000);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

function formatRelTime(logTs, runStartTs) {
  if (!runStartTs || !logTs) return null;
  const ms = new Date(logTs).getTime() - new Date(runStartTs).getTime();
  if (ms < 0) return null;
  if (ms < 1000) return `+${Math.round(ms)}ms`;
  return `+${(ms / 1000).toFixed(1)}s`;
}

function getSeverity(logs) {
  for (const l of logs) {
    const lv = (l.level || '').toUpperCase();
    if (lv === 'CRITICAL' || lv === 'ERROR') return 'error';
  }
  for (const l of logs) {
    if ((l.level || '').toUpperCase() === 'WARNING') return 'warning';
  }
  return 'ok';
}

// ─── Data builder ─────────────────────────────────────────────────────────────

/**
 * Groups sorted logs into context blocks — consecutive runs sharing the same
 * call_chain. Each context switch creates a new block, preserving real
 * chronological order (including all interleaving between functions).
 *
 * @returns {Array<ContextBlock>}
 *   ContextBlock: {
 *     id, chain, parts, fn, depth,
 *     logs, firstTs, lastTs, severity,
 *     totalOccurrences,   // how many times this chain appears in total
 *     occurrenceIndex,    // which occurrence this block is (1-based)
 *   }
 */
function buildContextBlocks(logs) {
  const sorted = [...logs].sort((a, b) => new Date(a.ts) - new Date(b.ts));
  const blocks = [];
  let cur = null;

  for (const log of sorted) {
    const chain = (log.context?.call_chain || '').trim();
    const parts = chain.split('>').map((s) => s.trim()).filter(Boolean);
    const fn    = parts.at(-1) || null;
    const ts    = new Date(log.ts).getTime();

    if (cur && cur.chain === chain) {
      cur.logs.push(log);
      if (ts > cur.lastTs) cur.lastTs = ts;
    } else {
      cur = {
        id:      blocks.length,
        chain,
        parts,
        fn,
        depth:   Math.max(1, parts.length),
        logs:    [log],
        firstTs: ts,
        lastTs:  ts,
      };
      blocks.push(cur);
    }
  }

  // Compute occurrence tracking (for loop/repeat indicators)
  const chainCount = {};
  const chainIdx   = {};
  for (const b of blocks) chainCount[b.chain] = (chainCount[b.chain] || 0) + 1;
  for (const b of blocks) {
    chainIdx[b.chain]      = (chainIdx[b.chain] || 0) + 1;
    b.severity             = getSeverity(b.logs);
    b.totalOccurrences     = chainCount[b.chain];
    b.occurrenceIndex      = chainIdx[b.chain];
  }

  return blocks;
}

// ─── Atoms ────────────────────────────────────────────────────────────────────

function StatusIcon({ severity, size = 14 }) {
  const cls = `shrink-0`; // size via style
  const style = { width: size, height: size };
  if (severity === 'error')   return <XCircle       className={cls} style={{ ...style, color: '#f43f5e' }} />;
  if (severity === 'warning') return <AlertTriangle className={cls} style={{ ...style, color: '#f59e0b' }} />;
  return                             <CheckCircle2  className={cls} style={{ ...style, color: '#10b981' }} />;
}

// ─── Log row ──────────────────────────────────────────────────────────────────

function LogRow({ log, runStartTs }) {
  const level = (log.level || 'INFO').toUpperCase();
  const badge = LEVEL_STYLE[level] || LEVEL_STYLE.INFO;
  const rel   = formatRelTime(log.ts, runStartTs);
  return (
    <div className="flex items-start gap-2 px-2 py-1.5 rounded-md hover:bg-black/[0.03] transition-colors">
      <span className={`shrink-0 mt-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded border ${badge}`}>
        {level.substring(0, 3)}
      </span>
      {rel && (
        <span className="shrink-0 mt-0.5 text-[10px] font-mono text-app-muted tabular-nums">{rel}</span>
      )}
      <span className="text-xs font-mono text-app-text leading-relaxed break-all">
        {log.message}
      </span>
    </div>
  );
}

// ─── Context block ────────────────────────────────────────────────────────────

const SEVERITY_BG = {
  error:   'rgba(254,226,226,0.4)',  // rose-100/40
  warning: 'rgba(254,243,199,0.35)', // amber-100/35
  ok:      '',
};

function ContextBlock({ block, runStartTs }) {
  // Expanded by default — the user sees the real log feed with context
  const [open, setOpen] = useState(true);

  const dur      = formatDuration(block.lastTs - block.firstTs);
  const isLoop   = block.totalOccurrences >= 3;
  const isRepeat = block.totalOccurrences === 2;

  // Indentation: depth 1 = 0px, depth 2 = 16px, depth 3 = 32px, capped at 64px
  const marginLeft = `${Math.min((block.depth - 1) * 16, 64)}px`;
  const borderColor = depthBorderColor(block.depth);
  const bgColor     = SEVERITY_BG[block.severity];

  return (
    <div style={{ marginLeft }}>
      {/* Block header */}
      <div
        onClick={() => setOpen((v) => !v)}
        className="flex flex-col rounded-xl border border-app-border/60 overflow-hidden cursor-pointer select-none transition-all duration-150 hover:border-app-border"
        style={{
          borderLeftWidth: 4,
          borderLeftColor: borderColor,
          backgroundColor: bgColor || undefined,
        }}
      >
        {/* Title row */}
        <div className="flex items-center gap-2 px-3 py-2">
          {open
            ? <ChevronDown  className="h-3.5 w-3.5 text-app-muted shrink-0" />
            : <ChevronRight className="h-3.5 w-3.5 text-app-muted shrink-0" />}

          <StatusIcon severity={block.severity} />

          {/* Function name */}
          <span className="flex-1 min-w-0 text-xs font-mono font-semibold text-app-text truncate">
            {block.fn || '(sem contexto)'}
          </span>

          {/* Loop indicator: ↻ N/total */}
          {isLoop && (
            <span className="shrink-0 flex items-center gap-0.5 text-[9px] font-bold text-violet-600 bg-violet-50 border border-violet-200 px-1.5 py-0.5 rounded-full tabular-nums">
              <RefreshCw className="h-2.5 w-2.5" />
              {block.occurrenceIndex}/{block.totalOccurrences}
            </span>
          )}
          {isRepeat && (
            <span className="shrink-0 text-[9px] font-bold text-app-muted bg-app-primary/10 border border-app-border/40 px-1.5 py-0.5 rounded-full">
              ×2
            </span>
          )}

          {/* Duration */}
          {dur && (
            <span className="shrink-0 text-[10px] font-mono text-app-muted tabular-nums">{dur}</span>
          )}

          {/* Log count */}
          <span className="shrink-0 text-[10px] text-app-muted bg-app-primary/10 px-2 py-0.5 rounded-full tabular-nums">
            {block.logs.length} {block.logs.length === 1 ? 'log' : 'logs'}
          </span>
        </div>

        {/* Breadcrumb — always visible, shows full call chain */}
        {block.parts.length > 0 && (
          <div className="px-3 pb-1.5 -mt-0.5 text-[10px] font-mono text-app-muted/50 truncate leading-none">
            {block.parts.join(' › ')}
          </div>
        )}
      </div>

      {/* Logs — grid accordion */}
      <div className={`grid transition-all duration-200 ${open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}>
        <div className="overflow-hidden">
          <div
            className="ml-2 mt-0.5 mb-1 pl-3 flex flex-col"
            style={{ borderLeft: `2px solid ${borderColor}30` }}
          >
            {block.logs.map((log, i) => (
              <LogRow key={i} log={log} runStartTs={runStartTs} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function ExecutionView({ runId, runStartTs }) {
  const [status, setStatus] = useState('loading');
  const [phase,  setPhase]  = useState(0);
  const [blocks, setBlocks] = useState(null);
  const [stats,  setStats]  = useState(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setStatus('loading');
      setPhase(0);
      try {
        const allLogs = [];
        let offset = 0;
        const PAGE = 500;
        while (true) {
          const page = await getRunLogs(runId, { limit: PAGE, offset, order: 'asc' });
          if (cancelled) return;
          allLogs.push(...page.items);
          if (allLogs.length >= page.total) break;
          offset += PAGE;
        }

        if (cancelled) return;
        setPhase(1);
        await new Promise((r) => setTimeout(r, 60));
        if (cancelled) return;

        const built = buildContextBlocks(allLogs);
        const loopChains = new Set(
          built.filter((b) => b.totalOccurrences >= 3).map((b) => b.chain)
        ).size;

        setBlocks(built);
        setStats({
          total:  allLogs.length,
          blocks: built.length,
          loops:  loopChains,
          orphan: built.filter((b) => !b.fn).reduce((s, b) => s + b.logs.length, 0),
        });
        setStatus('done');
      } catch {
        if (!cancelled) setStatus('error');
      }
    }

    load();
    return () => { cancelled = true; };
  }, [runId]);

  // ── Loading ─────────────────────────────────────────────────────────────────
  if (status === 'loading') {
    const msgs = ['Carregando logs…', 'Reconstruindo execução…'];
    return (
      <div className="flex flex-col items-center justify-center py-14 gap-5 animate-fade-in-up">
        <div className="relative h-14 w-14">
          <div className="absolute inset-0 rounded-full border-[3px] border-app-primary/20" />
          <div className="absolute inset-0 rounded-full border-[3px] border-t-app-accent border-r-transparent border-b-transparent border-l-transparent animate-spin" />
          <GitBranch className="absolute inset-0 m-auto h-5 w-5 text-app-accent" />
        </div>
        <div key={phase} className="text-center animate-fade-in-up">
          <p className="text-sm font-semibold text-app-text">{msgs[phase]}</p>
          <p className="text-[11px] text-app-muted mt-1">Aguarde um momento</p>
        </div>
        <div className="flex gap-2">
          {msgs.map((_, i) => (
            <div key={i} className={[
              'h-1.5 rounded-full transition-all duration-300',
              i < phase   ? 'w-5 bg-app-accent' :
              i === phase ? 'w-3 bg-app-accent/60 animate-pulse' :
                            'w-1.5 bg-app-primary/20',
            ].join(' ')} />
          ))}
        </div>
      </div>
    );
  }

  // ── Error ────────────────────────────────────────────────────────────────────
  if (status === 'error') {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-2 text-rose-500">
        <XCircle className="h-8 w-8" />
        <p className="text-sm font-semibold">Falha ao carregar logs</p>
      </div>
    );
  }

  // ── Empty ────────────────────────────────────────────────────────────────────
  if (!blocks?.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-2 text-app-muted">
        <GitBranch className="h-8 w-8 opacity-30" />
        <p className="text-sm font-semibold">Sem dados de rastreamento</p>
        <p className="text-xs text-center max-w-xs">
          Nenhum log possui <code className="font-mono text-app-accent">call_chain</code>.
        </p>
      </div>
    );
  }

  // ── View ─────────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-1">
      {/* Summary bar */}
      <div className="flex items-center gap-3 px-1 pb-2 mb-1 border-b border-app-border/50 text-[11px] text-app-muted flex-wrap">
        <GitBranch className="h-3.5 w-3.5 shrink-0" />
        <span>
          <span className="font-semibold text-app-text">{stats.total}</span> logs
        </span>
        <span>
          <span className="font-semibold text-app-text">{stats.blocks}</span> contextos
        </span>
        {stats.loops > 0 && (
          <span className="flex items-center gap-1">
            <RefreshCw className="h-3 w-3 text-violet-500" />
            <span className="font-semibold text-violet-600">{stats.loops}</span>{' '}
            loop{stats.loops > 1 ? 's' : ''} detectado{stats.loops > 1 ? 's' : ''}
          </span>
        )}
        {stats.orphan > 0 && (
          <span>
            <span className="font-semibold text-amber-600">{stats.orphan}</span> sem rastreamento
          </span>
        )}
      </div>

      {/* Feed cronológico de blocos de contexto */}
      {blocks.map((block) => (
        <ContextBlock key={block.id} block={block} runStartTs={runStartTs} />
      ))}
    </div>
  );
}
