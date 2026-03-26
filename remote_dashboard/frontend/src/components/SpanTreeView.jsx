import { useEffect, useState } from 'react';
import {
  AlertTriangle,
  ChevronDown,
  ChevronRight,
  GitBranch,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import { getRunLogs } from '../lib/api';

// ─── Constants ────────────────────────────────────────────────────────────────

const LEVEL_STYLE = {
  CRITICAL: 'bg-fuchsia-100 text-fuchsia-700 border-fuchsia-300',
  ERROR:    'bg-rose-100 text-rose-700 border-rose-300',
  WARNING:  'bg-amber-100 text-amber-700 border-amber-300',
  INFO:     'bg-emerald-100 text-emerald-700 border-emerald-200',
  DEBUG:    'bg-sky-100 text-sky-700 border-sky-200',
  SUCCESS:  'bg-green-100 text-green-700 border-green-200',
  SCREEN:   'bg-slate-100 text-slate-600 border-slate-200',
};

const DEPTH_COLORS = [
  'border-l-blue-400',
  'border-l-violet-400',
  'border-l-teal-400',
  'border-l-orange-400',
  'border-l-pink-400',
];

// ─── Helpers ──────────────────────────────────────────────────────────────────

function depthColor(depth) {
  return DEPTH_COLORS[Math.min(depth, DEPTH_COLORS.length - 1)];
}

function formatRelTime(logTs, runStartTs) {
  if (!runStartTs || !logTs) return null;
  const ms = new Date(logTs).getTime() - new Date(runStartTs).getTime();
  if (ms < 0) return null;
  if (ms < 1000) return `+${Math.round(ms)}ms`;
  return `+${(ms / 1000).toFixed(1)}s`;
}

function formatDuration(ms) {
  if (!ms || ms < 0) return null;
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const m = Math.floor(ms / 60_000);
  const s = Math.round((ms % 60_000) / 1000);
  return s > 0 ? `${m}m ${s}s` : `${m}m`;
}

// Normalize a message to a "template" by replacing digits/UUIDs with placeholders.
// Used to detect repeated patterns (loops).
function messageTemplate(msg) {
  return msg
    .replace(/\b\d+\b/g, 'N')
    .replace(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/gi, 'UUID')
    .trim();
}

// ─── Tree builder ─────────────────────────────────────────────────────────────

/**
 * Builds a tree of nodes from the logs' call_chain field.
 *
 * Each log's call_chain (e.g. "main>fetch_data>validate_row") describes the
 * path of functions that led to the log. We create one tree node per unique
 * path prefix and assign each log to its deepest node.
 *
 * Returns { roots, orphanLogs } where orphanLogs are logs with no call_chain.
 */
function buildTree(allLogs) {
  const nodeMap = {};

  function getOrCreate(path, name, parentPath) {
    if (!nodeMap[path]) {
      nodeMap[path] = {
        id: path,
        name,
        parentPath: parentPath || null,
        logs: [],
        children: [],
        firstTs: null,
        lastTs: null,
        severity: null,
        seq: 0,
      };
    }
    return nodeMap[path];
  }

  const orphanLogs = [];

  for (const log of allLogs) {
    const raw = log.context?.call_chain;
    if (!raw || typeof raw !== 'string') {
      orphanLogs.push(log);
      continue;
    }

    const parts = raw.split('>').map((s) => s.trim()).filter(Boolean);
    if (parts.length === 0) {
      orphanLogs.push(log);
      continue;
    }

    const logTs = new Date(log.ts).getTime();

    for (let i = 0; i < parts.length; i++) {
      const path = parts.slice(0, i + 1).join('>');
      const parentPath = i > 0 ? parts.slice(0, i).join('>') : null;
      const node = getOrCreate(path, parts[i], parentPath);
      if (node.firstTs === null || logTs < node.firstTs) node.firstTs = logTs;
      if (node.lastTs === null || logTs > node.lastTs) node.lastTs = logTs;
    }

    const deepPath = parts.join('>');
    nodeMap[deepPath].logs.push(log);
  }

  // Wire parent → children
  for (const node of Object.values(nodeMap)) {
    if (node.parentPath && nodeMap[node.parentPath]) {
      const parent = nodeMap[node.parentPath];
      if (!parent.children.find((c) => c.id === node.id)) {
        parent.children.push(node);
      }
    }
  }

  function sortNode(node) {
    node.children.sort((a, b) => (a.firstTs || 0) - (b.firstTs || 0));
    node.children.forEach((child, i) => {
      child.seq = i + 1;
      sortNode(child);
    });
    node.logs.sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());
  }

  function severityOf(node) {
    let worst = null;
    for (const log of node.logs) {
      const lv = (log.level || '').toUpperCase();
      if (lv === 'CRITICAL' || lv === 'ERROR') { worst = 'error'; break; }
      if (lv === 'WARNING') worst = 'warning';
    }
    for (const child of node.children) {
      const s = severityOf(child);
      if (s === 'error') { worst = 'error'; break; }
      if (s === 'warning' && worst !== 'error') worst = 'warning';
    }
    node.severity = worst;
    return worst;
  }

  const roots = Object.values(nodeMap).filter(
    (n) => !n.parentPath || !nodeMap[n.parentPath]
  );
  roots.sort((a, b) => (a.firstTs || 0) - (b.firstTs || 0));
  roots.forEach((r, i) => { r.seq = i + 1; sortNode(r); severityOf(r); });

  return { roots, orphanLogs };
}

// Interleave logs + child nodes in chronological order for rendering
function buildTimeline(node) {
  const items = [];
  for (const child of node.children) {
    items.push({ type: 'node', data: child, ts: child.firstTs || 0 });
  }
  for (const log of node.logs) {
    items.push({ type: 'log', data: log, ts: new Date(log.ts).getTime() });
  }
  items.sort((a, b) => a.ts - b.ts);
  return items;
}

/**
 * Groups consecutive logs with the same message template into RepeatGroups.
 * A RepeatGroup with count >= 2 collapses into a single row.
 */
function groupLogs(logs) {
  if (logs.length === 0) return [];
  const groups = [];
  let current = null;

  for (const log of logs) {
    const tmpl = messageTemplate(log.message || '');
    const level = (log.level || 'INFO').toUpperCase();
    if (current && current.template === tmpl && current.level === level) {
      current.logs.push(log);
    } else {
      current = { template: tmpl, level, logs: [log] };
      groups.push(current);
    }
  }

  return groups.map((g) =>
    g.logs.length === 1
      ? { type: 'single', log: g.logs[0] }
      : { type: 'repeat', logs: g.logs, count: g.logs.length, level: g.level, message: g.logs[0].message }
  );
}

/**
 * Detects loop-like patterns in a node's direct logs.
 * Returns { detected: bool, iterations: number, pattern: string } or null.
 *
 * Strategy: find the most common message template; if it repeats >= 3 times
 * and accounts for >= 40% of logs, we call it a loop.
 */
function detectLoop(logs) {
  if (logs.length < 3) return null;

  const templateCounts = {};
  for (const log of logs) {
    const tmpl = messageTemplate(log.message || '');
    templateCounts[tmpl] = (templateCounts[tmpl] || 0) + 1;
  }

  const entries = Object.entries(templateCounts).sort((a, b) => b[1] - a[1]);
  const [topTemplate, topCount] = entries[0];
  if (topCount < 3) return null;
  if (topCount / logs.length < 0.35) return null;

  // Try to find the actual example message (un-normalized)
  const example = logs.find((l) => messageTemplate(l.message || '') === topTemplate)?.message || topTemplate;

  return { detected: true, iterations: topCount, pattern: example };
}

// ─── Log row ──────────────────────────────────────────────────────────────────

function LogRow({ log, runStartTs }) {
  const level = (log.level || 'INFO').toUpperCase();
  const badgeClass = LEVEL_STYLE[level] || LEVEL_STYLE.INFO;
  const rel = formatRelTime(log.ts, runStartTs);

  return (
    <div className="flex items-start gap-2 px-2 py-1.5 rounded-lg hover:bg-app-primary/5 transition-colors">
      <span className={`shrink-0 mt-0.5 text-[9px] font-bold px-1.5 py-0.5 rounded border ${badgeClass}`}>
        {level.substring(0, 3)}
      </span>
      {rel && (
        <span className="shrink-0 mt-0.5 text-[10px] font-mono text-app-muted tabular-nums">
          {rel}
        </span>
      )}
      <span className="text-xs font-mono text-app-text leading-relaxed break-all">
        {log.message}
      </span>
    </div>
  );
}

// ─── Repeat group row ─────────────────────────────────────────────────────────

function RepeatGroupRow({ group, runStartTs }) {
  const [expanded, setExpanded] = useState(false);
  const level = group.level;
  const badgeClass = LEVEL_STYLE[level] || LEVEL_STYLE.INFO;

  return (
    <div className="rounded-lg border border-app-border/40 overflow-hidden">
      {/* Collapsed header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2 px-2 py-1.5 hover:bg-app-primary/5 transition-colors text-left"
      >
        <span className={`shrink-0 text-[9px] font-bold px-1.5 py-0.5 rounded border ${badgeClass}`}>
          {level.substring(0, 3)}
        </span>
        <span className="flex-1 min-w-0 text-xs font-mono text-app-text truncate">
          {group.message}
        </span>
        <span className="shrink-0 flex items-center gap-1 text-[10px] font-semibold text-app-muted bg-app-primary/10 px-2 py-0.5 rounded-full tabular-nums">
          <RefreshCw className="h-2.5 w-2.5" />
          ×{group.count}
        </span>
        <span className="shrink-0">
          {expanded
            ? <ChevronDown className="h-3 w-3 text-app-muted" />
            : <ChevronRight className="h-3 w-3 text-app-muted" />}
        </span>
      </button>

      {/* Expanded rows */}
      <div className={`grid transition-all duration-200 ${expanded ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}>
        <div className="overflow-hidden">
          <div className="border-t border-app-border/30 flex flex-col">
            {group.logs.map((log, i) => (
              <LogRow key={i} log={log} runStartTs={runStartTs} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Tree node ────────────────────────────────────────────────────────────────

function countLogs(node) {
  let count = node.logs.length;
  for (const child of node.children) count += countLogs(child);
  return count;
}

function TreeNode({ node, depth, runStartTs, defaultOpen }) {
  const [open, setOpen] = useState(defaultOpen ?? false);

  const timeline = buildTimeline(node);
  const hasContent = timeline.length > 0;
  const totalLogs = countLogs(node);
  const duration = formatDuration(node.lastTs && node.firstTs ? node.lastTs - node.firstTs : null);

  // Group only the direct logs of this node (not children)
  const groupedLogs = groupLogs(node.logs);
  // Loop detection on direct logs
  const loop = detectLoop(node.logs);

  // Build the renderable timeline: replace raw log items with grouped versions
  // We keep child-node items as-is, and replace log items with grouped ones.
  const renderItems = (() => {
    const childItems = node.children.map((child) => ({
      type: 'node',
      data: child,
      ts: child.firstTs || 0,
    }));

    // Build grouped log items preserving timestamps for sorting
    const logItems = groupedLogs.map((g) => {
      const ts = g.type === 'single'
        ? new Date(g.log.ts).getTime()
        : new Date(g.logs[0].ts).getTime();
      return { type: g.type === 'single' ? 'log' : 'repeat', data: g, ts };
    });

    return [...childItems, ...logItems].sort((a, b) => a.ts - b.ts);
  })();

  return (
    <div className="flex flex-col">
      {/* Header */}
      <div
        onClick={() => hasContent && setOpen((v) => !v)}
        className={[
          'flex items-center gap-2 px-3 py-2 rounded-xl',
          'border border-app-border border-l-4',
          depthColor(depth),
          'bg-app-elevated/80',
          hasContent
            ? 'cursor-pointer hover:bg-app-primary/5 hover:border-app-primary/20 active:scale-[0.995]'
            : 'cursor-default',
          'transition-all duration-150 select-none',
        ].join(' ')}
      >
        {/* Chevron */}
        <span className={`shrink-0 ${!hasContent ? 'opacity-0' : ''}`}>
          {open
            ? <ChevronDown className="h-3.5 w-3.5 text-app-accent" />
            : <ChevronRight className="h-3.5 w-3.5 text-app-muted" />}
        </span>

        {/* Seq badge */}
        <span className="shrink-0 text-[9px] font-bold tabular-nums text-app-muted bg-app-primary/10 rounded-full w-4 h-4 flex items-center justify-center">
          {node.seq}
        </span>

        {/* Function name */}
        <span className="flex-1 min-w-0 text-xs font-mono font-semibold text-app-text truncate">
          {node.name}
        </span>

        {/* Loop indicator */}
        {loop && (
          <span className="shrink-0 flex items-center gap-1 text-[9px] font-semibold text-violet-600 bg-violet-50 border border-violet-200 px-1.5 py-0.5 rounded-full">
            <RefreshCw className="h-2.5 w-2.5" />
            {loop.iterations}×
          </span>
        )}

        {/* Duration */}
        {duration && (
          <span className="shrink-0 text-[10px] font-mono text-app-muted tabular-nums">
            {duration}
          </span>
        )}

        {/* Log count */}
        {totalLogs > 0 && (
          <span className="shrink-0 text-[10px] text-app-muted bg-app-primary/10 px-2 py-0.5 rounded-full tabular-nums">
            {totalLogs} {totalLogs === 1 ? 'log' : 'logs'}
          </span>
        )}

        {/* Severity icon */}
        {node.severity === 'error' && (
          <XCircle className="shrink-0 h-3.5 w-3.5 text-rose-500" />
        )}
        {node.severity === 'warning' && (
          <AlertTriangle className="shrink-0 h-3.5 w-3.5 text-amber-500" />
        )}
      </div>

      {/* Expandable content — CSS grid accordion */}
      <div
        className={`grid transition-all duration-300 ease-in-out ${open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}
      >
        <div className="overflow-hidden">
          <div className="ml-5 mt-1 mb-0.5 pl-3 border-l-2 border-app-primary/15 flex flex-col gap-1">
            {renderItems.map((item, i) => {
              if (item.type === 'node') {
                return (
                  <TreeNode
                    key={item.data.id}
                    node={item.data}
                    depth={depth + 1}
                    runStartTs={runStartTs}
                    defaultOpen={false}
                  />
                );
              }
              if (item.type === 'repeat') {
                return (
                  <RepeatGroupRow key={i} group={item.data} runStartTs={runStartTs} />
                );
              }
              return <LogRow key={i} log={item.data.log || item.data} runStartTs={runStartTs} />;
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Orphan section ───────────────────────────────────────────────────────────

function OrphanSection({ logs, runStartTs }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="mt-1 rounded-xl border border-app-border/50 bg-app-elevated/60 overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-app-primary/5 transition-colors text-left"
      >
        {open
          ? <ChevronDown className="h-3.5 w-3.5 text-app-muted shrink-0" />
          : <ChevronRight className="h-3.5 w-3.5 text-app-muted shrink-0" />}
        <span className="text-[11px] font-semibold text-app-muted">
          {logs.length} logs sem rastreamento de chamada
        </span>
        <span className="text-[10px] text-app-muted/60 ml-auto">
          (emitidos sem call_chain registrado)
        </span>
      </button>
      <div className={`grid transition-all duration-300 ${open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'}`}>
        <div className="overflow-hidden">
          <div className="px-3 pb-3 flex flex-col">
            {logs.map((log, i) => (
              <LogRow key={i} log={log} runStartTs={runStartTs} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

export default function SpanTreeView({ runId, runStartTs }) {
  const [status, setStatus] = useState('loading');
  const [phase, setPhase]   = useState(0);
  const [treeData, setTreeData] = useState(null);

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

        const { roots, orphanLogs } = buildTree(allLogs);

        setTreeData({ roots, orphanLogs, totalLogs: allLogs.length });
        setStatus('done');
      } catch {
        if (!cancelled) setStatus('error');
      }
    }

    load();
    return () => { cancelled = true; };
  }, [runId]);

  // ── Loading ───────────────────────────────────────────────────────────────
  if (status === 'loading') {
    const msgs = ['Carregando logs...', 'Reconstruindo fluxo de execução...'];
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

  // ── Error ─────────────────────────────────────────────────────────────────
  if (status === 'error') {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-2 text-rose-500">
        <XCircle className="h-8 w-8" />
        <p className="text-sm font-semibold">Falha ao carregar logs</p>
      </div>
    );
  }

  const { roots, orphanLogs, totalLogs } = treeData;

  // ── Empty ─────────────────────────────────────────────────────────────────
  if (roots.length === 0 && orphanLogs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-2 text-app-muted">
        <GitBranch className="h-8 w-8 opacity-30" />
        <p className="text-sm font-semibold">Sem dados de rastreamento</p>
        <p className="text-xs text-center max-w-xs">
          Nenhum log desta execução possui <code className="font-mono text-app-accent">call_chain</code>.<br />
          Verifique se o formatter de console está habilitado.
        </p>
      </div>
    );
  }

  const trackedLogs = totalLogs - orphanLogs.length;

  // ── Tree ──────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col gap-1.5">
      {/* Summary */}
      <div className="flex items-center gap-3 px-1 pb-2 mb-1 border-b border-app-border/50 text-[11px] text-app-muted">
        <GitBranch className="h-3.5 w-3.5 shrink-0" />
        <span><span className="font-semibold text-app-text">{roots.length}</span> {roots.length === 1 ? 'função raiz' : 'funções raiz'}</span>
        <span><span className="font-semibold text-app-text">{trackedLogs}</span> logs rastreados</span>
        {orphanLogs.length > 0 && (
          <span><span className="font-semibold text-amber-600">{orphanLogs.length}</span> sem rastreamento</span>
        )}
      </div>

      {/* Root nodes — first 3 open by default */}
      {roots.map((root, i) => (
        <TreeNode
          key={root.id}
          node={root}
          depth={0}
          runStartTs={runStartTs}
          defaultOpen={i < 3}
        />
      ))}

      {/* Orphan logs */}
      {orphanLogs.length > 0 && (
        <OrphanSection logs={orphanLogs} runStartTs={runStartTs} />
      )}
    </div>
  );
}
