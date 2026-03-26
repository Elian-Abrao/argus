# Logger Agent

Runtime do agent que roda nas maquinas remotas e se conecta na Logger API para:

- identificar o host
- escanear automacoes locais
- manter conexao WebSocket persistente
- receber comandos `execute` e `kill`
- enviar heartbeat e status de execucao

## Estrutura

- `__main__.py`
  - entrypoint principal
- `config.py`
  - carga de configuracao via `agent_config.json` ou env vars
- `connection.py`
  - conexao WebSocket com a API
- `executor.py`
  - execucao e cancelamento de subprocessos
- `scanner.py`
  - scan de diretorios por `logger_config.json`
- `scripts/start_logger_agent.sh`
  - script de inicializacao com `git pull` e fallback
- `scripts/logger-agent.desktop`
  - template de autostart para abrir o agent em terminal visivel

## Requisitos

- Python 3
- virtualenv criado em `.venv`
- dependencias instaladas com:

```bash
pip install -r requirements.txt
```

- `agent_config.json` com `api_url` ou a variavel `AGENT_API_URL`

## Como iniciar manualmente

Se este repositorio estiver em `~/Scripts/Logger_Agent`, o fluxo usado na maquina pode ser:

```bash
cd ~/Scripts/Logger_Agent
git pull
source .venv/bin/activate
cd ..
python -m Logger_Agent
```

Se o nome do diretorio do checkout for outro, troque `Logger_Agent` pelo nome real da pasta.

## Autostart em terminal visivel

Para fazer o agent iniciar automaticamente ao entrar na sessao grafica Linux, use o script e o arquivo `.desktop` dentro de `scripts/`.

### 1. Copie o script para um local fixo

O autostart chama o script abaixo:

- `scripts/start_logger_agent.sh`

Uma opcao simples e manter o repo em `~/Scripts/Logger_Agent` e dar permissao de execucao:

```bash
cd ~/Scripts/Logger_Agent
chmod +x scripts/start_logger_agent.sh
```

Por padrao o script assume:

- repo em `~/Scripts/Logger_Agent`
- modulo Python `Logger_Agent`
- log em `~/logger-agent-start.log`

Se quiser, voce pode sobrescrever via variaveis:

```bash
REPO_DIR="$HOME/Scripts/Logger_Agent" MODULE_NAME="Logger_Agent" bash scripts/start_logger_agent.sh
```

### 2. O que o script faz

O script `scripts/start_logger_agent.sh`:

1. entra no repositorio do agent
2. espera alguns segundos para a rede subir
3. roda `git pull`
4. se o `git pull` falhar, continua com a versao atual
5. ativa o `.venv`
6. sobe o agent com `python -m <nome-do-modulo>`
7. grava tudo em `~/logger-agent-start.log`

### 3. Configure o autostart

Crie a pasta de autostart se necessario:

```bash
mkdir -p ~/.config/autostart
```

Copie o template:

```bash
cp ~/Scripts/Logger_Agent/scripts/logger-agent.desktop ~/.config/autostart/logger-agent.desktop
```

Depois ajuste o arquivo se precisar:

```bash
nano ~/.config/autostart/logger-agent.desktop
```

O template padrao usa:

```ini
[Desktop Entry]
Type=Application
Name=Logger Agent
Exec=gnome-terminal -- bash -lc '$HOME/Scripts/Logger_Agent/scripts/start_logger_agent.sh; echo; echo "Agent finalizado. Pressione Enter para fechar."; read'
X-GNOME-Autostart-enabled=true
Terminal=false
```

Esse fluxo abre um terminal visivel ao fazer login e mantem a janela aberta se o agent sair.

### 4. Testar sem reiniciar a maquina

Para abrir agora, sem reiniciar:

```bash
gnome-terminal -- bash -lc '$HOME/Scripts/Logger_Agent/scripts/start_logger_agent.sh; echo; echo "Agent finalizado. Pressione Enter para fechar."; read'
```

Ou rode o script diretamente:

```bash
bash ~/Scripts/Logger_Agent/scripts/start_logger_agent.sh
```

## Troubleshooting

### `No module named agent`

Isso costuma acontecer quando o checkout do repo esta com nome diferente de `agent` e o comando usado foi `python -m agent`.

Use o nome real da pasta do checkout, por exemplo:

```bash
cd ~/Scripts
python -m Logger_Agent
```

### `git pull` pede PAT

Se o remoto estiver em `https`, o Git pode pedir usuario e PAT. O script de autostart vai funcionar melhor se a autenticacao ja estiver resolvida na maquina.

### O terminal abre e fecha rapido

Rode o comando manualmente:

```bash
bash ~/Scripts/Logger_Agent/scripts/start_logger_agent.sh
```

Depois veja o log:

```bash
cat ~/logger-agent-start.log
```
