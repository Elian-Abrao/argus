import { Check, ChevronDown, ChevronRight, Copy, Database, Expand, Loader2, Minimize2, Search, Send, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getAuthHeaders } from '../lib/api';

const MIN_WIDTH = 320;
const MAX_WIDTH = 1100;
const DEFAULT_WIDTH = 384;
const EXPANDED_WIDTH = 680;

function AiAvatar({ size = 'sm', avatarUrl = '/ai/avatar.webp' }) {
  const sizes = { xs: 'h-5 w-5', sm: 'h-7 w-7', md: 'h-8 w-8', lg: 'h-12 w-12', xl: 'h-12 w-12' };
  return <img src={avatarUrl} alt="AI" className={`${sizes[size]} rounded-full object-cover`} />;
}

/* ─── ToolBadge ──────────────────────────────────────────────────── */

function ToolBadge({ tool }) {
  const isSearch = tool.name === 'search_objects';
  const Icon = isSearch ? Search : Database;

  if (tool.status === 'running') {
    return (
      <div className="flex items-center gap-1.5 rounded-md border border-violet-500/20 bg-violet-500/10 px-2 py-1 text-[11px] text-violet-300">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>{isSearch ? 'Buscando schema' : 'Consultando banco'}…</span>
      </div>
    );
  }

  if (tool.status === 'error') {
    return (
      <div className="flex items-center gap-1.5 rounded-md border border-red-500/20 bg-red-500/10 px-2 py-1 text-[11px] text-red-300">
        <Icon className="h-3 w-3" />
        <span>Erro: {tool.error}</span>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-1.5 rounded-md border border-app-border bg-app-surface/60 px-2 py-1 text-[11px] text-app-muted">
      <Icon className="h-3 w-3 text-violet-400" />
      <span>{isSearch ? 'Schema' : 'SQL'}</span>
      {tool.rows !== undefined && (
        <span className="text-violet-400">{tool.rows} linha{tool.rows !== 1 ? 's' : ''}</span>
      )}
    </div>
  );
}

/* ─── ThinkingSection ────────────────────────────────────────────── */

function ThinkingSection({ thinkingItems, currentRoundText, isStreaming, done }) {
  const [expanded, setExpanded] = useState(true);
  const prevDone = useRef(false);

  useEffect(() => {
    if (done && !prevDone.current) {
      const t = setTimeout(() => setExpanded(false), 600);
      prevDone.current = true;
      return () => clearTimeout(t);
    }
  }, [done]);

  const toolCount = thinkingItems.filter((i) => i.kind === 'tool').length;
  const hasContent = thinkingItems.length > 0 || currentRoundText;
  if (!hasContent) return null;

  const toolSummary = toolCount > 0
    ? ` · ${toolCount} consulta${toolCount !== 1 ? 's' : ''}`
    : '';

  return (
    <div className="mb-1.5 overflow-hidden rounded-xl border border-violet-500/15 bg-violet-500/5">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left hover:bg-violet-500/5 transition"
      >
        {isStreaming && !done ? (
          <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-violet-400" />
        ) : (
          <div className="h-3.5 w-3.5 shrink-0 text-violet-400">
            {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
          </div>
        )}
        <span className="text-[11px] font-medium text-violet-300">
          {isStreaming && !done ? 'Pensando…' : 'Raciocínio'}
        </span>
        <span className="text-[10px] text-app-muted">{toolSummary}</span>
      </button>

      {expanded && (
        <div className="border-t border-violet-500/10 px-3 pb-3 pt-2 space-y-1">
          {thinkingItems.map((item, i) =>
            item.kind === 'thinking' ? (
              <p key={i} className="text-[11px] leading-relaxed text-app-muted">
                — {item.text}
              </p>
            ) : (
              <div key={i} className="flex items-center gap-1.5 py-0.5">
                <span className="text-[11px] text-app-muted">—</span>
                <ToolBadge tool={item} />
              </div>
            )
          )}
          {currentRoundText && (
            <p className="text-[11px] leading-relaxed text-app-muted">
              — {currentRoundText}
              {isStreaming && <Loader2 className="ml-1 inline h-2.5 w-2.5 animate-spin text-violet-400" />}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/* ─── Markdown components ────────────────────────────────────────── */

const markdownComponents = {
  p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="mb-2 list-disc pl-4 space-y-0.5">{children}</ul>,
  ol: ({ children }) => <ol className="mb-2 list-decimal pl-4 space-y-0.5">{children}</ol>,
  li: ({ children }) => <li className="text-sm">{children}</li>,
  h1: ({ children }) => <h1 className="mb-2 text-base font-semibold">{children}</h1>,
  h2: ({ children }) => <h2 className="mb-1.5 text-sm font-semibold">{children}</h2>,
  h3: ({ children }) => <h3 className="mb-1 text-sm font-medium">{children}</h3>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  em: ({ children }) => <em className="italic">{children}</em>,
  code: ({ inline, children }) =>
    inline ? (
      <span className="font-semibold text-app-text">{children}</span>
    ) : (
      <code className="block overflow-x-auto rounded-lg bg-black/30 p-3 font-mono text-[11px] text-app-text leading-relaxed whitespace-pre">
        {children}
      </code>
    ),
  pre: ({ children }) => <pre className="mb-2 last:mb-0">{children}</pre>,
  blockquote: ({ children }) => (
    <blockquote className="mb-2 border-l-2 border-violet-500/40 pl-3 text-app-muted italic">
      {children}
    </blockquote>
  ),
  table: ({ children }) => (
    <div className="mb-2 overflow-x-auto">
      <table className="w-full border-collapse text-xs">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead>{children}</thead>,
  tbody: ({ children }) => <tbody>{children}</tbody>,
  tr: ({ children }) => <tr className="border-b border-app-border">{children}</tr>,
  th: ({ children }) => (
    <th className="border border-app-border bg-app-surface/60 px-2 py-1 text-left font-semibold text-app-text">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="border border-app-border px-2 py-1 text-app-text">{children}</td>
  ),
  a: ({ href, children }) => {
    const isInternal = href && href.startsWith('/');
    return (
      <a
        href={href}
        onClick={isInternal ? (e) => { e.preventDefault(); window.__aiChatNavigate?.(href); } : undefined}
        target={isInternal ? undefined : '_blank'}
        rel={isInternal ? undefined : 'noopener noreferrer'}
        className="text-violet-400 underline hover:text-violet-300"
      >
        {children}
      </a>
    );
  },
  hr: () => <hr className="my-2 border-app-border" />,
};

/* ─── CopyButton ─────────────────────────────────────────────────── */

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      title="Copiar resposta"
      className="absolute right-2 top-2 flex h-6 w-6 items-center justify-center rounded-md text-transparent transition-colors hover:text-violet-400 hover:bg-violet-500/10 group-hover:text-app-muted"
    >
      {copied ? <Check className="h-3 w-3 text-violet-400" /> : <Copy className="h-3 w-3" />}
    </button>
  );
}

/* ─── Message ────────────────────────────────────────────────────── */

function Message({ msg, avatarUrl }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-violet-600 px-3.5 py-2.5 text-sm text-white">
          {msg.content}
        </div>
      </div>
    );
  }

  const items = msg.thinkingItems || [];
  const hasThinking = items.length > 0 || msg.currentRoundText;
  const displayText = msg.content;

  return (
    <div className="flex gap-2.5">
      <div className="mt-0.5 shrink-0">
        <AiAvatar size="sm" avatarUrl={avatarUrl} />
      </div>
      <div className="flex min-w-0 max-w-[85%] flex-col gap-1">
        {hasThinking && (
          <ThinkingSection
            thinkingItems={items}
            currentRoundText={msg.currentRoundText || ''}
            isStreaming={!msg.done}
            done={msg.done}
          />
        )}

        {displayText ? (
          <div className="group relative rounded-2xl rounded-tl-sm bg-app-elevated px-3.5 py-2.5 text-sm text-app-text leading-relaxed">
            {msg.done && <CopyButton text={msg.content} />}
            <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
              {displayText}
            </ReactMarkdown>
          </div>
        ) : !hasThinking && !msg.done ? (
          <div className="flex items-center gap-2 rounded-2xl rounded-tl-sm bg-app-elevated px-3.5 py-2.5">
            <Loader2 className="h-3.5 w-3.5 animate-spin text-violet-400" />
            <span className="text-sm text-app-muted">Pensando…</span>
          </div>
        ) : null}
      </div>
    </div>
  );
}

/* ─── AiChatWidget ──────────────────────────────────────────────── */

export default function AiChatWidget({
  aiName = 'Argus AI',
  aiGreeting = 'Hello! How can I help?',
  avatarUrl = '/ai/avatar.webp',
}) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [panelWidth, setPanelWidth] = useState(DEFAULT_WIDTH);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const [hasUnread, setHasUnread] = useState(false);
  const [askContinue, setAskContinue] = useState(null); // { sessionId, rounds }
  const bottomRef = useRef(null);
  const inputRef = useRef(null);
  const openRef = useRef(open);
  useEffect(() => { openRef.current = open; }, [open]);

  // Expose navigate for markdown link clicks
  useEffect(() => {
    window.__aiChatNavigate = (path) => navigate(path);
    return () => { delete window.__aiChatNavigate; };
  }, [navigate]);
  const historyRef = useRef([]);

  // ── Resize drag ───────────────────────────────────────────────────
  const isResizing = useRef(false);
  const resizeStartX = useRef(0);
  const resizeStartWidth = useRef(0);

  const handleResizeMove = useCallback((e) => {
    if (!isResizing.current) return;
    const delta = resizeStartX.current - e.clientX;
    setPanelWidth(Math.max(MIN_WIDTH, Math.min(MAX_WIDTH, resizeStartWidth.current + delta)));
  }, []);

  const handleResizeEnd = useCallback(() => {
    isResizing.current = false;
    document.removeEventListener('mousemove', handleResizeMove);
    document.removeEventListener('mouseup', handleResizeEnd);
    document.body.style.userSelect = '';
    document.body.style.cursor = '';
  }, [handleResizeMove]);

  const handleResizeStart = useCallback((e) => {
    e.preventDefault();
    isResizing.current = true;
    resizeStartX.current = e.clientX;
    resizeStartWidth.current = panelWidth;
    document.addEventListener('mousemove', handleResizeMove);
    document.addEventListener('mouseup', handleResizeEnd);
    document.body.style.userSelect = 'none';
    document.body.style.cursor = 'col-resize';
  }, [panelWidth, handleResizeMove, handleResizeEnd]);

  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', handleResizeMove);
      document.removeEventListener('mouseup', handleResizeEnd);
    };
  }, [handleResizeMove, handleResizeEnd]);

  // ── Scroll & focus ────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 100);
  }, [open]);

  // ── Send ──────────────────────────────────────────────────────────
  const sendMessage = async () => {
    if (!input.trim() || streaming) return;

    const question = input.trim();
    setInput('');
    setStreaming(true);

    setMessages((prev) => [...prev, { role: 'user', content: question }]);
    setMessages((prev) => [
      ...prev,
      { role: 'assistant', content: '', thinkingItems: [], currentRoundText: '', done: false },
    ]);

    let finalContent = '';

    try {
      const response = await fetch('/dashboard-api/ai/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ question, history: historyRef.current, current_page: window.location.pathname + window.location.search }),
      });

      if (!response.ok || !response.body) {
        throw new Error('Falha ao abrir stream do assistente');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      const processSseChunk = (chunk, isFinal = false) => {
        buffer += chunk;
        const lines = buffer.split('\n');
        buffer = isFinal ? '' : (lines.pop() ?? '');
        const completeLines = isFinal ? lines.filter((line) => line.length > 0) : lines;

        for (const line of completeLines) {
          if (!line.startsWith('data: ')) continue;
          let data;
          try { data = JSON.parse(line.slice(6)); } catch { continue; }

          if (data.type === 'thinking_delta') {
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              next[next.length - 1] = { ...last, currentRoundText: (last.currentRoundText || '') + data.text };
              return next;
            });
          } else if (data.type === 'finalize') {
            finalContent = data.text;
            if (!openRef.current) setHasUnread(true);
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              // Flush remaining thinking text before finalizing
              const items = [...(last.thinkingItems || [])];
              const remainingText = (last.currentRoundText || '').trim();
              if (remainingText) items.push({ kind: 'thinking', text: remainingText });
              next[next.length - 1] = {
                ...last,
                content: finalContent,
                thinkingItems: items,
                currentRoundText: '',
                done: true,
              };
              return next;
            });
          } else if (data.type === 'tool_start') {
            setMessages((prev) => {
              const next = [...prev];
              const last = { ...next[next.length - 1] };
              const items = [...(last.thinkingItems || [])];
              // Flush currentRoundText como item de thinking
              const roundText = (last.currentRoundText || '').trim();
              if (roundText) items.push({ kind: 'thinking', text: roundText });
              // Adiciona tool como item cronológico
              items.push({ kind: 'tool', name: data.tool, args: data.args, status: 'running' });
              next[next.length - 1] = { ...last, thinkingItems: items, currentRoundText: '' };
              return next;
            });
          } else if (data.type === 'tool_result') {
            setMessages((prev) => {
              const next = [...prev];
              const last = { ...next[next.length - 1] };
              const items = [...(last.thinkingItems || [])];
              // Atualiza o último tool item
              for (let i = items.length - 1; i >= 0; i--) {
                if (items[i].kind === 'tool' && items[i].status === 'running') {
                  items[i] = { ...items[i], rows: data.rows, status: 'done' };
                  break;
                }
              }
              next[next.length - 1] = { ...last, thinkingItems: items };
              return next;
            });
          } else if (data.type === 'tool_error') {
            setMessages((prev) => {
              const next = [...prev];
              const last = { ...next[next.length - 1] };
              const items = [...(last.thinkingItems || [])];
              for (let i = items.length - 1; i >= 0; i--) {
                if (items[i].kind === 'tool' && items[i].status === 'running') {
                  items[i] = { ...items[i], error: data.error, status: 'error' };
                  break;
                }
              }
              next[next.length - 1] = { ...last, thinkingItems: items };
              return next;
            });
          } else if (data.type === 'delta') {
            // Fallback: delta legado — acumula como conteúdo direto
            finalContent += data.text;
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { ...next[next.length - 1], content: finalContent };
              return next;
            });
          } else if (data.type === 'done') {
            if (!openRef.current) setHasUnread(true);
            setMessages((prev) => {
              const next = [...prev];
              const last = next[next.length - 1];
              // Flush any remaining currentRoundText into thinkingItems
              const items = [...(last.thinkingItems || [])];
              const remainingText = (last.currentRoundText || '').trim();
              if (remainingText && !last.content && !finalContent) {
                // Text sem tool call = resposta final, não thinking
              } else if (remainingText) {
                items.push({ kind: 'thinking', text: remainingText });
              }
              const resolvedContent = last.content || finalContent || last.currentRoundText || 'Não foi possível montar uma resposta final.';
              next[next.length - 1] = {
                ...last,
                content: resolvedContent,
                thinkingItems: items,
                currentRoundText: '',
                done: true,
              };
              return next;
            });
            historyRef.current = [
              ...historyRef.current,
              { role: 'user', content: question },
              { role: 'assistant', content: finalContent || 'Resposta processada.' },
            ];
          } else if (data.type === 'ask_continue') {
            setAskContinue({ sessionId: data.session_id, rounds: data.rounds });
          } else if (data.type === 'limit_reached') {
            setAskContinue(null);
          } else if (data.type === 'error') {
            setMessages((prev) => {
              const next = [...prev];
              next[next.length - 1] = { ...next[next.length - 1], content: data.text, done: true };
              return next;
            });
          }
        }
      };

      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          processSseChunk(decoder.decode(), true);
          break;
        }
        processSseChunk(decoder.decode(value, { stream: true }));
      }
    } catch {
      setMessages((prev) => {
        const next = [...prev];
        next[next.length - 1] = {
          ...next[next.length - 1],
          content: 'Não foi possível conectar com o assistente. Tente novamente.',
          done: true,
        };
        return next;
      });
    } finally {
      setStreaming(false);
    }
  };

  const sendContinueDecision = async (decision) => {
    if (!askContinue) return;
    const { sessionId } = askContinue;
    setAskContinue(null);
    try {
      await fetch('/dashboard-api/ai/chat/continue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
        body: JSON.stringify({ session_id: sessionId, decision }),
      });
    } catch {
      // Stream will timeout eventually if request fails
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (askContinue && input.trim()) {
        sendContinueDecision(input.trim());
        setInput('');
      } else {
        sendMessage();
      }
    }
  };

  const isExpanded = panelWidth >= EXPANDED_WIDTH;

  return (
    <>
      {/* Botão flutuante */}
      <button
        data-tour="ai-button"
        type="button"
        onClick={() => { setOpen(true); setHasUnread(false); }}
        className={`fixed bottom-5 right-5 z-40 flex h-12 w-12 items-center justify-center rounded-full bg-violet-600 shadow-lg shadow-violet-900/50 transition-all hover:bg-violet-500 hover:scale-105 active:scale-95 ${open ? 'opacity-0 pointer-events-none' : 'opacity-100'}`}
        title={`Abrir ${aiName}`}
      >
        <img src={avatarUrl} alt={aiName} className="h-9 w-9 rounded-full object-cover" />
        {hasUnread && (
          <span className="absolute -top-0.5 -right-0.5 h-3.5 w-3.5 rounded-full bg-red-500 ring-2 ring-app-bg animate-pulse" />
        )}
      </button>

      {/* Painel lateral */}
      <div
        className={`fixed inset-y-0 right-0 z-50 flex flex-col border-l border-app-border bg-app-bg shadow-2xl shadow-black/40 transition-[transform] duration-300 ${open ? 'translate-x-0' : 'translate-x-full'}`}
        style={{ width: `${panelWidth}px` }}
      >
        {/* Handle de resize — borda esquerda arrastável */}
        <div
          className="absolute left-0 top-0 h-full w-1 cursor-col-resize bg-transparent hover:bg-violet-500/40 transition-colors"
          onMouseDown={handleResizeStart}
          title="Arraste para redimensionar"
        />

        {/* Header */}
        <div className="flex items-center justify-between border-b border-app-border bg-app-elevated px-4 py-3">
          <div className="flex items-center gap-2.5">
            <AiAvatar size="md" avatarUrl={avatarUrl} />
            <div>
              <p className="text-sm font-semibold text-app-text">{aiName}</p>
              <p className="text-[10px] text-app-muted">Assistente de dados</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => setPanelWidth(isExpanded ? DEFAULT_WIDTH : EXPANDED_WIDTH)}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-app-muted hover:bg-app-surface hover:text-app-text transition"
              title={isExpanded ? 'Diminuir' : 'Expandir'}
            >
              {isExpanded ? <Minimize2 className="h-4 w-4" /> : <Expand className="h-4 w-4" />}
            </button>
            <button
              type="button"
              onClick={() => setOpen(false)}
              className="flex h-7 w-7 items-center justify-center rounded-lg text-app-muted hover:bg-app-surface hover:text-app-text transition"
              title="Fechar"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Mensagens */}
        <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
          {messages.length === 0 && (
            <div className="flex flex-col items-center gap-3 pt-8 text-center">
              <img src={`${avatarUrl.replace('avatar.webp', 'greeting.webp')}`} alt={aiName} className="h-24 w-auto object-contain" />
              <p className="text-sm font-medium text-app-text">{aiGreeting}</p>
              <p className="text-xs text-app-muted leading-relaxed">
                Posso consultar os dados e responder perguntas sobre clientes, automações, execuções e logs.
              </p>
              <div className="mt-2 flex flex-col gap-1.5 w-full">
                {[
                  'Algum robô falhou hoje? Me mostre o erro.',
                  'Quais clientes tiveram execuções com problema essa semana?',
                  'O agendamento de hoje foi executado normalmente?',
                  'Me dê um resumo do que aconteceu hoje nas automações.',
                ].map((suggestion) => (
                  <button
                    key={suggestion}
                    type="button"
                    onClick={() => { setInput(suggestion); inputRef.current?.focus(); }}
                    className="flex items-center gap-2 rounded-xl border border-app-border bg-app-surface/60 px-3 py-2 text-left text-xs text-app-text hover:border-violet-500/40 hover:bg-violet-500/10 transition"
                  >
                    <ChevronRight className="h-3 w-3 shrink-0 text-violet-400" />
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg, i) => (
            <Message key={i} msg={msg} avatarUrl={avatarUrl} />
          ))}
          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <div className="border-t border-app-border bg-app-elevated p-3">
          {/* Ask continue — option bubbles */}
          {askContinue && (
            <div className="mb-2 flex flex-wrap gap-1.5">
              <p className="w-full text-[11px] text-app-muted mb-1">
                Já fiz {askContinue.rounds} consultas. Deseja que eu continue?
              </p>
              <button
                type="button"
                onClick={() => sendContinueDecision('continue')}
                className="rounded-lg border border-violet-500/30 bg-violet-500/10 px-3 py-1.5 text-xs font-medium text-violet-300 hover:bg-violet-500/20 transition"
              >
                Continuar pesquisando
              </button>
              <button
                type="button"
                onClick={() => sendContinueDecision('stop')}
                className="rounded-lg border border-app-border bg-app-surface/60 px-3 py-1.5 text-xs font-medium text-app-muted hover:bg-app-surface transition"
              >
                Responder agora
              </button>
            </div>
          )}

          <div className="flex items-end gap-2 rounded-xl border border-app-border bg-app-surface/80 px-3 py-2 focus-within:border-violet-500/60 transition">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={askContinue ? 'Ou digite uma instrução…' : 'Pergunte algo…'}
              rows={1}
              disabled={streaming && !askContinue}
              className="flex-1 resize-none bg-transparent text-sm text-app-text placeholder:text-app-muted focus:outline-none disabled:opacity-50"
              style={{ maxHeight: '120px' }}
              onInput={(e) => {
                e.target.style.height = 'auto';
                e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
              }}
            />
            <button
              type="button"
              onClick={() => {
                if (askContinue && input.trim()) {
                  sendContinueDecision(input.trim());
                  setInput('');
                } else {
                  sendMessage();
                }
              }}
              disabled={askContinue ? !input.trim() : (!input.trim() || streaming)}
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-violet-600 text-white transition hover:bg-violet-500 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {streaming && !askContinue ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
            </button>
          </div>
          <p className="mt-1.5 text-center text-[10px] text-app-muted">Enter para enviar · Shift+Enter para nova linha</p>
        </div>
      </div>

      {/* Overlay escuro ao abrir no mobile */}
      {open && (
        <div className="fixed inset-0 z-40 bg-black/30 lg:hidden" onClick={() => setOpen(false)} />
      )}
    </>
  );
}
