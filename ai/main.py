from __future__ import annotations

from src.agent.chat import (
    BRIDGE_URL,
    BridgeClientError,
    ask_data_assistant,
    get_codex_limit_message,
    is_codex_usage_limit_error,
)
from src.mcp_server.runtime import DBHUB_LOG_PATH


def main() -> int:
    history: list[dict[str, str]] = []
    print("Argus AI — data assistant. Type 'sair' to exit.\n")

    while True:
        try:
            user_question = input("Pergunta: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_question:
            continue

        if user_question.lower() in ("sair", "exit", "quit"):
            break

        print()
        try:
            answer = ask_data_assistant(user_question, history)
        except BridgeClientError as exc:
            if is_codex_usage_limit_error(exc):
                answer = get_codex_limit_message()
                print(answer)
                print()
                history.append({"role": "user", "content": user_question})
                history.append({"role": "assistant", "content": answer})
                continue
            print(f"\nFalha ao chamar o codex-bridge em {BRIDGE_URL}: {exc}")
            print("Confirme se o broker foi autenticado com `codex-bridge login` e iniciado com `codex-bridge serve`.")
            return 2
        except RuntimeError as exc:
            print(f"\n{exc}")
            print(f"Verifique o log do DBHub em {DBHUB_LOG_PATH}.")
            return 3

        print()
        history.append({"role": "user", "content": user_question})
        history.append({"role": "assistant", "content": answer})

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
