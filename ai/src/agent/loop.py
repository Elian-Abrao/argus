from __future__ import annotations

import json
import re
from collections.abc import Generator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..mcp_server.dbhub_client import DbhubClient, DbhubClientError
from ..mcp_server.runtime import ensure_dbhub_running
from ..config import get_dbhub_settings, AI_NAME, PLATFORM_NAME
from ..mcp_server.schema import get_schema_context

_PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"

# Tipo dos eventos emitidos pelo gerador web
Event = dict[str, Any]

# Regex para limpar ecos de tool result que o modelo pode inserir na resposta
_TOOL_ECHO_START_RE = re.compile(r"Resultado da ferramenta `[^`]+`:\s*\{")
_TOOL_RESULT_TAG_RE = re.compile(r"<tool_result>\s*[\s\S]*?\s*</tool_result>\s*", re.DOTALL)


def _strip_tool_result_echoes(text: str) -> str:
    result = _TOOL_RESULT_TAG_RE.sub("", text)
    while True:
        match = _TOOL_ECHO_START_RE.search(result)
        if not match:
            break
        brace_start = match.end() - 1
        depth = 0
        pos = brace_start
        found_end = False
        while pos < len(result):
            ch = result[pos]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    tail = result[pos + 1:]
                    result = result[: match.start()] + tail.lstrip()
                    found_end = True
                    break
            pos += 1
        if not found_end:
            break
    return result.lstrip()


def _finalize_text(output_text: str) -> str:
    clean = _strip_tool_result_echoes(output_text).strip()
    return clean if clean else (output_text or "").strip()


_AGENT_SYSTEM = (
    (_PROMPTS_DIR / "system.md")
    .read_text(encoding="utf-8")
    .replace("{AI_NAME}", AI_NAME)
    .replace("{PLATFORM_NAME}", PLATFORM_NAME)
)


# ---------------------------------------------------------------------------
# Tool definitions (OpenAI function calling format)
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "name": "execute_sql",
        "description": "Executa um SELECT no PostgreSQL do Logger. Apenas SELECT ou WITH...SELECT. Sempre use LIMIT.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "A consulta SQL SELECT a executar",
                }
            },
            "required": ["sql"],
            "additionalProperties": False,
        },
    },
    {
        "type": "function",
        "name": "search_objects",
        "description": "Busca tabelas, colunas ou schemas pelo nome no banco PostgreSQL.",
        "parameters": {
            "type": "object",
            "properties": {
                "object_type": {
                    "type": "string",
                    "enum": ["table", "column", "schema"],
                    "description": "Tipo de objeto a buscar",
                },
                "pattern": {
                    "type": "string",
                    "description": "Padrão de busca SQL LIKE (ex: %palavra%)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Máximo de resultados (default 10)",
                },
                "detail_level": {
                    "type": "string",
                    "enum": ["names", "details"],
                    "description": "Nível de detalhe (default names)",
                },
            },
            "required": ["object_type", "pattern"],
            "additionalProperties": False,
        },
    },
]


@dataclass
class UserContext:
    is_restricted: bool = True   # Fail-closed: restrito por padrão
    instance_ids: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserContext":
        return cls(
            is_restricted=bool(data.get("is_restricted", True)),
            instance_ids=[str(i) for i in data.get("instance_ids", [])],
        )

    @classmethod
    def unrestricted(cls) -> "UserContext":
        return cls(is_restricted=False, instance_ids=[])


MAX_ROUNDS = 10
_DEFAULT_TIMEOUT = 20.0
_SLOW_TIMEOUT = 130.0


def _is_timeout_error(exc: RuntimeError) -> bool:
    msg = str(exc).lower()
    return any(
        word in msg
        for word in ("timed out", "timeout", "deadline", "canceled", "cancelled", "tempo limite")
    )


def _make_dbhub_client(timeout: float) -> DbhubClient:
    ensure_dbhub_running()
    return DbhubClient(url=get_dbhub_settings().url, timeout=timeout)


# ---------------------------------------------------------------------------
# Controle de acesso: CTE shadow tables
# ---------------------------------------------------------------------------

def _build_access_cte(instance_ids: list[str]) -> str:
    # Filter is anchored on automation_instance IDs — not automation type IDs.
    # This prevents cross-client data leakage when the same automation type is
    # deployed for multiple clients.
    values = ", ".join(f"('{i}'::uuid)" for i in instance_ids)
    return f"""-- Controle de acesso: dados visíveis apenas para as instâncias autorizadas
_inst_filter(id) AS (VALUES {values}),
_run_filter(id) AS (
    SELECT id FROM runs WHERE automation_instance_id IN (SELECT id FROM _inst_filter)
),
_email_filter(id) AS (
    SELECT id FROM email_events WHERE run_id IN (SELECT id FROM _run_filter)
),
hosts AS (
    SELECT * FROM hosts WHERE id IN (SELECT DISTINCT host_id FROM automation_instances WHERE id IN (SELECT id FROM _inst_filter))
),
automation_instances AS (
    SELECT ai.* FROM automation_instances ai WHERE ai.id IN (SELECT id FROM _inst_filter)
),
clients AS (
    SELECT c.* FROM clients c
    WHERE c.id IN (SELECT DISTINCT client_id FROM automation_instances WHERE id IN (SELECT id FROM _inst_filter))
),
automations AS (
    SELECT a.* FROM automations a
    WHERE a.id IN (SELECT DISTINCT automation_id FROM automation_instances WHERE id IN (SELECT id FROM _inst_filter))
),
scheduled_jobs AS (
    SELECT * FROM scheduled_jobs WHERE automation_instance_id IN (SELECT id FROM _inst_filter)
),
runs AS (
    SELECT * FROM runs WHERE id IN (SELECT id FROM _run_filter)
),
log_entries AS (
    SELECT * FROM log_entries WHERE run_id IN (SELECT id FROM _run_filter)
),
run_snapshots AS (
    SELECT * FROM run_snapshots WHERE run_id IN (SELECT id FROM _run_filter)
),
commands AS (
    SELECT * FROM commands WHERE run_id IN (SELECT id FROM _run_filter)
),
email_events AS (
    SELECT * FROM email_events WHERE id IN (SELECT id FROM _email_filter)
),
email_attachments AS (
    SELECT * FROM email_attachments WHERE email_event_id IN (SELECT id FROM _email_filter)
),
client_automations AS (
    SELECT * FROM client_automations WHERE automation_instance_id IN (SELECT id FROM _inst_filter)
),
host_automations AS (
    SELECT * FROM host_automations WHERE automation_instance_id IN (SELECT id FROM _inst_filter)
)"""


def _strip_schema_prefix(sql: str) -> str:
    """Remove schema qualifications (e.g. public.clients → clients).

    PostgreSQL CTEs only shadow unqualified table names. If the LLM generates
    ``FROM public.clients`` the shadow CTE is bypassed completely. Stripping
    the prefix ensures every table reference goes through the shadow.
    """
    import re
    return re.sub(r'\bpublic\.', '', sql, flags=re.IGNORECASE)


def _inject_access_filter(sql: str, instance_ids: list[str]) -> str:
    cte_block = _build_access_cte(instance_ids)
    stripped = _strip_schema_prefix(sql.strip())
    upper = stripped.upper()
    if upper.startswith("WITH ") or upper.startswith("WITH\n") or upper.startswith("WITH\t"):
        after_with = stripped[4:].strip()
        return f"WITH\n{cte_block},\n{after_with}"
    return f"WITH\n{cte_block}\n{stripped}"


def _run_tool(tool_name: str, input_payload: Any, timeout: float, ctx: UserContext | None = None) -> dict[str, Any]:
    if tool_name == "execute_sql":
        dbhub = _make_dbhub_client(timeout)
        dbhub.initialize()
        sql = input_payload.get("sql") if isinstance(input_payload, dict) else str(input_payload)

        if ctx is None:
            print("[SECURITY] _run_tool: ctx=None — bloqueando SQL por segurança")
            sql = "SELECT 'Sem contexto de acesso' AS mensagem WHERE false"
        elif ctx.is_restricted and ctx.instance_ids:
            print(f"[ACCESS] Filtro CTE aplicado — {len(ctx.instance_ids)} instância(s) autorizadas")
            sql = _inject_access_filter(sql, ctx.instance_ids)
        elif ctx.is_restricted and not ctx.instance_ids:
            print("[ACCESS] Usuário restrito sem instâncias — bloqueando SQL")
            sql = "SELECT 'Sem acesso: nenhuma automação atribuída a este usuário' AS mensagem WHERE false"
        else:
            print(f"[ACCESS] Acesso irrestrito — is_restricted={ctx.is_restricted}")

        result = dbhub.call_tool("execute_sql", {"sql": sql})
    elif tool_name == "search_objects":
        dbhub = _make_dbhub_client(timeout)
        dbhub.initialize()
        args = input_payload if isinstance(input_payload, dict) else {}
        result = dbhub.call_tool("search_objects", args)
    else:
        raise ValueError(f"Ferramenta desconhecida: {tool_name}")

    if isinstance(result, dict) and result.get("success") is False:
        error_msg = result.get("error") or result.get("message") or "DBHub retornou erro na ferramenta."
        raise DbhubClientError(str(error_msg))

    return result


def _row_count(result: dict[str, Any]) -> int | str:
    rows = result.get("data", {}).get("rows") if isinstance(result, dict) else None
    return len(rows) if isinstance(rows, list) else "?"


def _extract_rows(result: dict[str, Any] | None) -> list[Any]:
    if not isinstance(result, dict):
        return []
    rows = result.get("data", {}).get("rows")
    return rows if isinstance(rows, list) else []


def _format_value(value: Any) -> str:
    if value is None:
        return "nulo"
    if isinstance(value, bool):
        return "sim" if value else "não"
    return str(value)


def _build_result_fallback(question: str, tool_results: list[dict[str, Any]]) -> str:
    successful_results = [item for item in tool_results if not item.get("error")]
    if not successful_results:
        errors = [item.get("error") for item in tool_results if item.get("error")]
        if errors:
            return f"Não consegui concluir a consulta. Último erro: {errors[-1]}"
        return "Não encontrei dados suficientes para montar uma resposta."

    last_result = successful_results[-1].get("result")
    rows = _extract_rows(last_result)
    question_lower = (question or "").strip().lower()

    if not rows:
        return "Não encontrei dados para responder a essa pergunta."

    if len(rows) == 1 and isinstance(rows[0], dict):
        row = rows[0]
        if len(row) == 1:
            only_value = next(iter(row.values()))
            if any(term in question_lower for term in ("quantas", "quantos", "número", "numero", "total")):
                return f"O total encontrado foi { _format_value(only_value) }."
            return f"Encontrei o seguinte valor: { _format_value(only_value) }."

        parts = [f"{key}: {_format_value(value)}" for key, value in row.items()]
        return "Encontrei este resultado:\n- " + "\n- ".join(parts)

    if len(rows) <= 5 and all(isinstance(row, dict) for row in rows):
        rendered_rows = []
        for idx, row in enumerate(rows, start=1):
            parts = [f"{key}: {_format_value(value)}" for key, value in row.items()]
            rendered_rows.append(f"{idx}. " + " | ".join(parts))
        return "Encontrei estes resultados:\n" + "\n".join(rendered_rows)

    return f"Encontrei {len(rows)} registros que atendem ao filtro da sua pergunta."


# ---------------------------------------------------------------------------
# Streaming round with native tool calling
# ---------------------------------------------------------------------------

def _iter_stream_round(
    client: Any,
    messages: list[dict[str, Any]],
    model: str,
    reasoning_effort: str,
    tools: list[dict[str, Any]] | None = None,
) -> Generator[Event, None, None]:
    """Stream one model round via bridge. Yields thinking_delta, _text, and _tool_call events."""
    request_payload: dict[str, Any] = {
        "model": model,
        "reasoningEffort": reasoning_effort,
        "executionMode": "agent",
        "messages": messages,
    }
    if tools:
        request_payload["tools"] = tools

    text_buffer: list[str] = []
    tool_call: dict[str, Any] | None = None

    for event in client.iter_stream_chat(request_payload):
        kind = str(event.get("kind", ""))

        if kind == "delta":
            delta = str(event.get("delta", ""))
            text_buffer.append(delta)
            yield {"type": "thinking_delta", "text": delta}

        elif kind == "tool_call_start":
            tool_call = {
                "name": event.get("name", ""),
                "call_id": event.get("callId", ""),
                "arguments": "",
            }

        elif kind == "tool_call_delta":
            if tool_call is not None:
                tool_call["arguments"] += event.get("delta", "")

        elif kind == "tool_call_done":
            call_id = event.get("callId", "")
            name = event.get("name", "")
            arguments = event.get("arguments", "")
            if tool_call is None:
                tool_call = {"name": name, "call_id": call_id, "arguments": arguments}
            else:
                tool_call["arguments"] = arguments
                if not tool_call["name"]:
                    tool_call["name"] = name
                if not tool_call["call_id"]:
                    tool_call["call_id"] = call_id
            yield {"type": "_tool_call", **tool_call}
            tool_call = None

        elif kind == "error":
            raise RuntimeError(event.get("message", "Unknown error"))

    yield {"type": "_text", "text": "".join(text_buffer)}


def _stream_round(client: Any, messages: list[dict[str, Any]], model: str, reasoning_effort: str) -> str:
    """CLI version: stream to stdout, return full text."""
    buffer: list[str] = []
    for event in client.iter_stream_chat(
        {"model": model, "reasoningEffort": reasoning_effort, "messages": messages}
    ):
        if str(event.get("kind")) != "delta":
            continue
        delta = str(event.get("delta", ""))
        buffer.append(delta)
        print(delta, end="", flush=True)
    return "".join(buffer)


def run_agentic_loop(
    question: str,
    history: list[dict[str, str]],
    client: Any,
    model: str,
    reasoning_effort: str,
) -> str:
    """Run the agentic loop (CLI): Codex calls tools until it has enough data to answer."""
    schema = get_schema_context()

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _AGENT_SYSTEM},
        {"role": "system", "content": "SCHEMA:\n" + schema},
        *history,
        {"role": "user", "content": question},
    ]

    rounds_done = 0

    while True:
        for _ in range(MAX_ROUNDS):
            # CLI uses native tools too
            tool_call_data = None
            output_text = ""
            for event in _iter_stream_round(client, messages, model, reasoning_effort, TOOL_DEFINITIONS):
                if event["type"] == "_text":
                    output_text = event["text"]
                elif event["type"] == "_tool_call":
                    tool_call_data = event
                elif event["type"] == "thinking_delta":
                    pass  # already printed by _iter_stream_round via delta

            if tool_call_data is None:
                print()
                return output_text

            tool_name = tool_call_data["name"]
            call_id = tool_call_data["call_id"]
            try:
                input_payload = json.loads(tool_call_data["arguments"])
            except json.JSONDecodeError:
                input_payload = {}
            rounds_done += 1

            args_str = json.dumps(input_payload, ensure_ascii=False)
            if len(args_str) > 120:
                args_str = args_str[:120] + "..."
            icon = "🔍" if tool_name == "search_objects" else "🔧"
            print(f"\n{icon} {tool_name}({args_str})")

            try:
                result = _run_tool(tool_name, input_payload, _DEFAULT_TIMEOUT)
                print(f"   ✓ {_row_count(result)} linha(s)\n")
            except (DbhubClientError, ValueError) as exc:
                result = {"error": str(exc)}
                print(f"   ✗ Erro: {exc}\n")

            # Add tool call + result as structured messages
            if output_text:
                messages.append({"role": "assistant", "content": output_text})
            messages.append({"role": "tool_call", "name": tool_name, "call_id": call_id, "arguments": tool_call_data["arguments"]})
            messages.append({"role": "tool_result", "call_id": call_id, "output": json.dumps(result, ensure_ascii=False)})

        print(
            f"\n⏸  Atingi {rounds_done} consultas. Deseja que eu continue pesquisando? [s/N] ",
            end="",
            flush=True,
        )
        try:
            choice = input().strip().lower()
        except (EOFError, KeyboardInterrupt):
            choice = "n"

        if choice in ("s", "sim", "y", "yes"):
            print("🔄 Continuando pesquisa…\n")
            continue
        else:
            break

    print("[gerando resposta com os dados disponíveis]\n")
    messages.append({"role": "user", "content": "Responda agora com os dados que você já coletou."})
    final = _stream_round(client, messages, model, reasoning_effort)
    print()
    return final


def iter_agentic_loop(
    question: str,
    history: list[dict[str, str]],
    client: Any,
    model: str,
    reasoning_effort: str,
    ask_continue_fn: Any = None,
    user_context: Any = None,
    user_info: dict[str, str] | None = None,
    current_page: str = "",
) -> Generator[Event, None, None]:
    """Versão geradora do loop agêntico para uso na API web (SSE).

    Emite eventos:
      {"type": "thinking_delta", "text": "..."}             — raciocínio em tempo real
      {"type": "tool_start", "tool": "...", "args": "..."}  — ferramenta chamada
      {"type": "tool_result", "rows": N}                    — ferramenta retornou N linhas
      {"type": "tool_error", "error": "..."}                — ferramenta falhou
      {"type": "slow_query"}                                 — timeout; retry automático
      {"type": "finalize", "text": "..."}                   — resposta final limpa
      {"type": "ask_continue", "rounds": N}                 — limite atingido
      {"type": "limit_reached"}                             — usuário recusou continuar
    """
    # Normaliza user_context
    if isinstance(user_context, dict):
        ctx = UserContext.from_dict(user_context)
    elif isinstance(user_context, UserContext):
        ctx = user_context
    elif hasattr(user_context, "model_dump"):
        ctx = UserContext.from_dict(user_context.model_dump())
    elif hasattr(user_context, "dict"):
        ctx = UserContext.from_dict(user_context.dict())
    else:
        print(f"[SECURITY] user_context não reconhecido ({type(user_context)}) — assumindo restrito")
        ctx = UserContext()

    print(f"[ACCESS] ctx: is_restricted={ctx.is_restricted}, instance_ids_count={len(ctx.instance_ids)}")

    schema = get_schema_context()

    # Mensagem de restrição de acesso
    access_note: list[dict[str, str]] = []
    if ctx.is_restricted:
        if ctx.instance_ids:
            access_note = [{"role": "system", "content": (
                f"RESTRIÇÃO DE ACESSO: Este usuário tem acesso a {len(ctx.instance_ids)} instância(s) de automação. "
                "Todos os dados são automaticamente filtrados no banco de dados para essas instâncias. "
                "Não mencione a existência de outros clientes, hosts ou automações fora desse escopo."
            )}]
        else:
            access_note = [{"role": "system", "content": (
                "RESTRIÇÃO DE ACESSO: Este usuário não tem acesso a nenhuma automação. "
                "Não há dados disponíveis para exibir. Informe o usuário de forma amigável que não há dados acessíveis."
            )}]

    # Contexto do usuário logado
    user_note: list[dict[str, str]] = []
    if user_info and user_info.get("name"):
        parts = [f"Usuário logado: {user_info['name']}"]
        if user_info.get("email"):
            parts.append(f"Email: {user_info['email']}")
        if user_info.get("role"):
            parts.append(f"Perfil: {user_info['role']}")
        if current_page:
            parts.append(f"Tela atual: {current_page}")
        user_note = [{"role": "system", "content": " | ".join(parts)}]

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _AGENT_SYSTEM},
        {"role": "system", "content": "SCHEMA:\n" + schema},
        *access_note,
        *user_note,
        *history,
        {"role": "user", "content": question},
    ]

    rounds_done = 0
    tool_results: list[dict[str, Any]] = []

    while True:
        for _ in range(MAX_ROUNDS):
            output_text = ""
            tool_call_data: dict[str, Any] | None = None

            for event in _iter_stream_round(client, messages, model, reasoning_effort, TOOL_DEFINITIONS):
                if event["type"] == "_text":
                    output_text = event["text"]
                elif event["type"] == "_tool_call":
                    tool_call_data = event
                else:
                    yield event  # thinking_delta em tempo real

            if tool_call_data is None:
                # Sem tool call — resposta final
                final_text = _finalize_text(output_text) or _build_result_fallback(question, tool_results)
                yield {"type": "finalize", "text": final_text}
                return

            tool_name = tool_call_data["name"]
            call_id = tool_call_data["call_id"]
            try:
                input_payload = json.loads(tool_call_data["arguments"])
            except json.JSONDecodeError:
                input_payload = {}
            rounds_done += 1

            args_preview = json.dumps(input_payload, ensure_ascii=False)
            if len(args_preview) > 120:
                args_preview = args_preview[:120] + "..."

            yield {"type": "tool_start", "tool": tool_name, "args": args_preview}

            try:
                try:
                    result = _run_tool(tool_name, input_payload, _DEFAULT_TIMEOUT, ctx)
                except DbhubClientError as exc:
                    if not _is_timeout_error(exc):
                        raise
                    yield {"type": "slow_query"}
                    result = _run_tool(tool_name, input_payload, _SLOW_TIMEOUT, ctx)

                yield {"type": "tool_result", "rows": _row_count(result)}
                tool_results.append({"tool": tool_name, "result": result})
            except (DbhubClientError, ValueError) as exc:
                result = {"error": str(exc)}
                yield {"type": "tool_error", "error": str(exc)}
                tool_results.append({"tool": tool_name, "error": str(exc), "result": result})

            # Add model text + structured tool call + result to messages
            if output_text:
                messages.append({"role": "assistant", "content": output_text})
            messages.append({"role": "tool_call", "name": tool_name, "call_id": call_id, "arguments": tool_call_data["arguments"]})
            messages.append({"role": "tool_result", "call_id": call_id, "output": json.dumps(result, ensure_ascii=False)})

        # MAX_ROUNDS esgotados
        yield {"type": "ask_continue", "rounds": rounds_done}

        decision = ask_continue_fn() if ask_continue_fn else False
        if not decision:
            break
        # Se o usuário enviou uma mensagem personalizada, injeta como contexto
        if isinstance(decision, str) and decision not in ("continue", "true", "True"):
            messages.append({"role": "user", "content": decision})

    # Força resposta final
    yield {"type": "limit_reached"}
    messages.append({"role": "user", "content": "Responda agora com os dados que você já coletou."})
    output_text = ""
    for event in _iter_stream_round(client, messages, model, reasoning_effort):
        if event["type"] == "_text":
            output_text = event["text"]
        elif event["type"] != "_tool_call":
            yield event
    final_text = _finalize_text(output_text) or _build_result_fallback(question, tool_results)
    yield {"type": "finalize", "text": final_text}


__all__ = ["run_agentic_loop", "iter_agentic_loop"]
