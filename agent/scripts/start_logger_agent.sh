#!/usr/bin/env bash

set -u

REPO_DIR="${REPO_DIR:-$HOME/Scripts/Logger_Agent}"
MODULE_NAME="${MODULE_NAME:-Logger_Agent}"
LOG_FILE="${LOG_FILE:-$HOME/logger-agent-start.log}"
NETWORK_WAIT_SECONDS="${NETWORK_WAIT_SECONDS:-8}"

{
  echo "======================================"
  echo "Inicio: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "Repo: $REPO_DIR"
  echo "Modulo: $MODULE_NAME"

  cd "$REPO_DIR" || {
    echo "Erro: nao consegui entrar em $REPO_DIR"
    exit 1
  }

  echo "Aguardando rede subir..."
  sleep "$NETWORK_WAIT_SECONDS"

  echo "Tentando git pull..."
  if git pull; then
    echo "git pull OK"
  else
    echo "git pull falhou, seguindo com a versao atual"
  fi

  echo "Ativando venv..."
  source .venv/bin/activate || {
    echo "Erro: nao consegui ativar .venv em $REPO_DIR"
    exit 1
  }

  echo "Subindo agent..."
  cd .. || exit 1
  exec python -m "$MODULE_NAME"
} 2>&1 | tee -a "$LOG_FILE"
