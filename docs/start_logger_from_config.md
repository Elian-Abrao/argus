# start_logger_from_config
[Voltar ao indice](README.md)

Este guia cobre em detalhes o helper `start_logger_from_config`, que permite
iniciar o logger usando um arquivo JSON (ou dict) com parametros.

## O que ele faz
- Carrega configuracoes externas (JSON ou dict).
- Valida chaves permitidas.
- Aplica overrides opcionais.
- Chama `start_logger` com o resultado final.

## Assinatura
```python
start_logger_from_config(config, overrides=None) -> logging.Logger
```

## Onde esta
- Implementacao: `logger/core/logger_core.py`
- Funcao exportada via pacote `logger`

## Formatos aceitos
### 1) Caminho de arquivo
```python
from logger import start_logger_from_config

logger = start_logger_from_config("logger_config.json")
```

### 2) dict em memoria
```python
from logger import start_logger_from_config

config = {
    "name": "Batch",
    "log_dir": "Logs",
    "console_level": "INFO",
    "file_level": "DEBUG",
    "capture_prints": True,
}
logger = start_logger_from_config(config)
```

### 3) JSON com bloco `start_logger`
Se o JSON vier organizado por secao, o helper usa o bloco `start_logger`:
```json
{
  "start_logger": {
    "name": "Batch",
    "console_level": "INFO",
    "capture_prints": true
  }
}
```

## Chaves permitidas
Somente as chaves abaixo sao aceitas (qualquer outra gera `ValueError`):
- `name`
- `log_dir`
- `console_level`
- `file_level`
- `capture_prints`
- `capture_emails`
- `email_retention_days`
- `verbose`
- `show_all_leaks`
- `watch_objects`
- `cleanup_days`
- `server_mode`
- `rotation_interval`
- `rotation_unit`
- `remote_sink`

## Tabela de chaves e usos principais
| Chave | Tipo | Uso principal |
|---|---|---|
| `name` | `str` ou `null` | Nome do logger e base do arquivo `.log`. |
| `log_dir` | `str` | Diretorio onde os logs sao salvos. |
| `console_level` | `str` | Nivel mostrado no console (INFO, WARNING, etc.). |
| `file_level` | `str` | Nivel gravado nos arquivos. |
| `capture_prints` | `bool` | Redireciona `print()` para o logger. |
| `capture_emails` | `bool` | Captura envios de email via `smtplib`. |
| `email_retention_days` | `int` ou `null` | Retencao de email (dias) para a automacao. |
| `verbose` | `int` | Aumenta detalhes no log de arquivo. |
| `show_all_leaks` | `bool` | Mostra todas as diferencas na checagem de memoria. |
| `watch_objects` | `list[str]` | Tipos/nomes para monitorar vazamentos. |
| `cleanup_days` | `int` ou `null` | Remove logs antigos antes de iniciar. |
| `server_mode` | `bool` | Evita snapshot inicial (servicos). |
| `rotation_interval` | `int` ou `null` | Intervalo de rotacao dos arquivos. |
| `rotation_unit` | `str` | Unidade da rotacao: `minutes`, `hours`, `days`. |
| `remote_sink` | `dict` ou `null` | Envio remoto para a API. |

## Detalhe por chave

### name
Define o nome do logger e o prefixo do arquivo `.log`.
- Use nomes curtos e estaveis (ex.: `ETL`, `API`).
- Quando `null`, o logger usa um nome padrao.

### log_dir
Diretorio base para os arquivos de log.
- Exemplo: `Logs` ou `C:/Logs/MinhaApp`.
- O logger cria subpastas necessarias (ex.: `LogsDEBUG`).

### console_level
Nivel exibido no console (`INFO`, `WARNING`, `ERROR`, `DEBUG`).
- Recomenda-se `INFO` em producao.
- Nivel invalido gera erro em runtime.

### file_level
Nivel gravado nos arquivos de log.
- Normalmente `DEBUG` para manter historico detalhado.

### capture_prints
Quando `true`, intercepta `print()` e registra no log.
- Evita logs perdidos em scripts legados.
- Pode ser desativado em sistemas com stdout controlado.

### capture_emails
Quando `true`, intercepta `smtplib.SMTP.sendmail` e `send_message`.
- Registra metadados de email no log (`EMAIL_CAPTURE ...`).
- Com `remote_sink`, envia auditoria para a API (evento + anexos).

### email_retention_days
Quantidade de dias para reter auditoria de emails.
- Usado como default do `remote_sink.email_retention_days`.
- Se ausente, a API usa o padrao global configurado no servidor.

### verbose
Controla o detalhamento do formato de arquivo.
- `0`: formato simples.
- `1`: adiciona call chain.
- `2`: adiciona `pathname:lineno`.
- `3+`: adiciona thread + detalhes maximos.

### show_all_leaks
Controla a exibicao da checagem de memoria ao final.
- `false`: mostra apenas diferencas relevantes.
- `true`: mostra todas as diferencas encontradas.

### watch_objects
Lista de tipos ou nomes de classes para monitorar vazamentos.
- Exemplo: `["DataFrame", "Session"]`.
- Os itens sao tratados como referencias para o monitoramento interno.

### cleanup_days
Remove arquivos `.log` mais antigos que N dias.
- Use para evitar crescimento infinito.
- Exemplo: `30` para manter apenas o ultimo mes.

### server_mode
Voltado para servicos de longa duracao.
- Pula o snapshot inicial de memoria.
- Mantem banners de inicio/fim.

### rotation_interval
Intervalo para rotacao de arquivos quando o processo fica ativo.
- Exemplo: `24` com `rotation_unit="hours"`.
- Nao ativa rotacao quando `null` ou `0`.

### rotation_unit
Unidade da rotacao: `minutes`, `hours` ou `days`.
- Obrigatorio quando `rotation_interval` esta definido.
- Qualquer outro valor gera `ValueError`.

### remote_sink
Configura envio remoto para a API.
- Exemplo minimo:
  ```json
  "remote_sink": {
    "enabled": true,
    "endpoint": "http://localhost:8100/api"
  }
  ```
- Campos comuns: `automation`, `client`, `host`, `deployment_tag`,
  `batch_size`, `flush_interval`.
- Consulte `docs/remote_api.md` para detalhes dos campos esperados.

## Overrides
`overrides` permite substituir valores do JSON sem alterar o arquivo.
Somente chaves permitidas sao aplicadas.

```python
logger = start_logger_from_config(
    "logger_config.json",
    overrides={"console_level": "WARNING", "server_mode": True},
)
```

## Exemplo completo
`logger_config.json`:
```json
{
  "name": "ETL",
  "log_dir": "Logs",
  "console_level": "INFO",
  "file_level": "DEBUG",
  "capture_prints": true,
  "capture_emails": true,
  "email_retention_days": 7,
  "verbose": 1,
  "cleanup_days": 15,
  "rotation_interval": 24,
  "rotation_unit": "hours",
  "server_mode": false,
  "remote_sink": {
    "enabled": true,
    "endpoint": "http://localhost:8100/api",
    "automation": {"code": "InvoiceBot", "name": "Invoice Bot"},
    "client": {"name": "Cliente XPTO", "external_code": "XPTO"},
    "host": {"environment": "prod"},
    "deployment_tag": "prod-01",
    "batch_size": 25,
    "flush_interval": 0.5
  }
}
```

Uso:
```python
from logger import start_logger_from_config

logger = start_logger_from_config("logger_config.json")
logger.info("Logger iniciado via config externa")
```

## Comportamentos importantes
- Chaves desconhecidas geram erro para evitar typos silenciosos.
- Se `server_mode=True`, o snapshot inicial de memoria e ignorado.
- Se `capture_prints=True`, `print()` passa a ser registrado.
- Se `capture_emails=True`, envios via `smtplib` passam a gerar eventos de auditoria.
- `rotation_interval` exige `rotation_unit` valido: `minutes`, `hours` ou `days`.
- `remote_sink.enabled=false` ou ausencia de `remote_sink` desativa o envio remoto.

## Erros comuns
| Erro | Causa | Solucao |
|---|---|---|
| `ValueError: Parametros desconhecidos...` | Chave nao suportada no JSON | Corrija o nome da chave |
| `rotation_unit invalida` | Unidade diferente de `minutes`, `hours`, `days` | Ajuste o JSON |
| `FileNotFoundError` | Caminho do JSON incorreto | Verifique o path |

## Quando usar
- Padronizar configuracoes entre ambientes.
- Evitar codigo duplicado em varios scripts.
- Facilitar ajustes em producao sem alterar codigo.

## Relacionado
- `docs/advanced_config.md`
- `docs/api_reference.md`
- `docs/examples.md`
