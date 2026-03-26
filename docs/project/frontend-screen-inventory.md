# Inventario de Telas do Frontend

Este documento descreve o que existe hoje no dashboard React em `remote_dashboard/frontend/`, com foco em telas, overlays e capacidades visiveis ao usuario.

## Escopo lido

- rotas em `remote_dashboard/frontend/src/App.jsx`
- shell e navegacao em `remote_dashboard/frontend/src/layout/`
- paginas em `remote_dashboard/frontend/src/pages/`
- modais e widgets em `remote_dashboard/frontend/src/components/`
- cliente HTTP em `remote_dashboard/frontend/src/lib/api.js`
- documentacao correlata em `README.md`, `CLAUDE.md`, `docs/project/frontend-dashboard.md` e `docs/project/endpoints-and-flows.md`

## Visao geral do produto

O dashboard e uma SPA React servida por FastAPI. O frontend nao fala com `/api` diretamente: toda chamada passa pelo proxy same-origin em `/dashboard-api/*`.

As capacidades do painel se distribuem em cinco blocos:

1. observabilidade operacional
2. inventario de hosts, robos e clientes
3. rastreamento de execucoes e logs
4. controle remoto via agendamentos e comandos
5. autenticacao, perfil, administracao e assistente de IA

## Navegacao principal

Menu lateral principal em `remote_dashboard/frontend/src/layout/panelNavigation.js`:

- `Visao Geral` -> `/`
- `Maquinas` -> `/hosts`
- `Robos` -> `/automations`
- `Clientes` -> `/clients`
- `Execucoes` -> `/runs`
- `Agendamentos` -> `/schedules`
- `Comandos` -> `/commands`

Recursos sempre presentes no shell (`PanelLayout.jsx`):

- breadcrumb dinamico por rota
- acao de atualizar no header, quando a pagina registra refresh
- atalho para perfil do usuario autenticado
- logout
- `AiChatWidget`, exibido globalmente como assistente lateral

## Rotas mapeadas

Rotas registradas em `remote_dashboard/frontend/src/App.jsx`:

- `/login`
- `/`
- `/hosts`
- `/hosts/:hostId`
- `/automations`
- `/automations/:automationId/runs`
- `/instances/:instanceId/runs`
- `/clients`
- `/clients/:clientId`
- `/runs`
- `/runs/:runId`
- `/schedules`
- `/commands`
- `/profile`
- `/admin/users`
- `/404`

## Telas

### 1. Login

- rota: `/login`
- arquivo: `remote_dashboard/frontend/src/pages/LoginPage.jsx`
- objetivo:
  autenticar o usuario para acesso ao painel.
- elementos principais:
  logo, campos de email e senha, feedback de erro e botao de envio.
- funcionalidades:
  autentica via `/dashboard-api/auth/login`, carrega o usuario atual e redireciona para `/`.
- observacoes:
  restauracao de sessao por refresh cookie e refresh proativo ficam centralizados em `remote_dashboard/frontend/src/lib/auth.jsx`.

### 2. Visao Geral

- rota: `/`
- arquivo: `remote_dashboard/frontend/src/pages/DashboardPage.jsx`
- objetivo:
  oferecer leitura rapida do estado operacional recente.
- dados carregados:
  hosts, automations, clients, timeline de runs, calendario de schedules e historico de commands.
- elementos principais:
  chips de metricas, grafico de status do dia, grafico de volume por horario, timeline ou lista de execucoes do dia e checklist de agendamentos.
- funcionalidades:
  refresh manual pelo header, alternancia entre timeline visual e lista textual, consolidacao de volumes e status, leitura de execucoes concorrentes.
- comportamento relevante:
  usa recorte do ultimo dia util local para montar o overview.

### 3. Inventario de Maquinas

- rota: `/hosts`
- arquivo: `remote_dashboard/frontend/src/pages/HostsPage.jsx`
- objetivo:
  listar hosts cadastrados e permitir filtragem operacional.
- elementos principais:
  metricas de hosts, robos, ambientes e hosts com IP; filtros por busca geral, hostname, IP e ambiente; tabela de hosts.
- funcionalidades:
  filtrar inventario, limpar filtros, navegar para detalhe do host.
- colunas relevantes:
  hostname, IP, ambiente, raiz, quantidade de robos e ultimo contato.

### 4. Detalhe de Maquina

- rota: `/hosts/:hostId`
- arquivo: `remote_dashboard/frontend/src/pages/HostDetailPage.jsx`
- objetivo:
  detalhar um host especifico e as instancias de automacao alocadas nele.
- elementos principais:
  metricas do host, tabela de instancias vinculadas e CTA de voltar.
- funcionalidades:
  exibir IP, ambiente, ultima atividade, numero de robos alocados, abrir execucoes por instancia e abrir execucoes por automacao.

### 5. Catalogo de Automacoes

- rota: `/automations`
- arquivo: `remote_dashboard/frontend/src/pages/AutomationsPage.jsx`
- objetivo:
  mostrar o catalogo de robos e sua distribuicao operacional.
- elementos principais:
  busca por nome/codigo, metricas agregadas, tabela clicavel por automacao.
- funcionalidades:
  navegar para historico de execucoes da automacao, abrir detalhes em modal, filtrar por busca textual.
- colunas relevantes:
  robo, equipe, instancias, hosts, clientes e ultima execucao.

### 6. Detalhe operacional de Automacao

- entrada:
  modal aberto a partir de `/automations`
- arquivos:
  `remote_dashboard/frontend/src/components/AutomationModal.jsx`
  `remote_dashboard/frontend/src/components/InstanceArgsModal.jsx`
- objetivo:
  detalhar uma automacao sem sair da listagem principal.
- elementos principais:
  cabecalho com nome, codigo, equipe e descricao; metricas; tabela de instancias implantadas.
- funcionalidades:
  refresh do modal, ir para historico da automacao, abrir runs da instancia, abrir gerenciamento de argumentos por instancia.
- tabela de instancias:
  cliente, host, IP, deployment, total de execucoes, ultimo run e acesso ao modal de argumentos.

### 7. Cadastro de Argumentos de Instancia

- entrada:
  modal secundario disparado do `AutomationModal`
- arquivo: `remote_dashboard/frontend/src/components/InstanceArgsModal.jsx`
- objetivo:
  modelar argumentos aceitos por uma instancia para substituir texto livre por controles estruturados.
- funcionalidades:
  criar, editar e remover argumentos do tipo `named`, `flag` e `positional`, definir descricao, valores permitidos e posicao, persistir em `/dashboard-api/instances/:id/args`.
- impacto funcional:
  esses argumentos depois aparecem estruturados no fluxo de `Iniciar Agora` e `Novo Agendamento`.

### 8. Carteira de Clientes

- rota: `/clients`
- arquivo: `remote_dashboard/frontend/src/pages/ClientsPage.jsx`
- objetivo:
  listar clientes e o volume de relacoes com automacoes.
- elementos principais:
  metricas agregadas, busca por cliente/codigo, tabela de clientes.
- funcionalidades:
  filtrar carteira, navegar para detalhe do cliente.
- colunas relevantes:
  nome, codigo externo, contato, quantidade de robos, instancias e ultima atividade.

### 9. Detalhe de Cliente

- rota: `/clients/:clientId`
- arquivo: `remote_dashboard/frontend/src/pages/ClientDetailPage.jsx`
- objetivo:
  mostrar a relacao entre um cliente e as automacoes/hosts em que ele esta implantado.
- elementos principais:
  metricas do cliente e tabela de automacoes vinculadas.
- funcionalidades:
  visualizar codigo, volume de robos, instancias, ultima atividade e o mapa de automacao x host x deployment.
- observacao:
  o link da coluna `Automacao` aponta para `/automations/:automation_id`; essa rota de detalhe dedicada nao existe no `App.jsx`, entao hoje esse link tende a cair no `404`. O detalhe real da automacao esta no modal da pagina `/automations`.

### 10. Historico Global de Execucoes

- rota: `/runs`
- arquivo: `remote_dashboard/frontend/src/pages/RunsPage.jsx`
- objetivo:
  centralizar a consulta de runs em nivel global.
- elementos principais:
  filtros por busca, cliente, host, status e periodo; ordenacao; metricas; graficos agregados; tabela paginada.
- funcionalidades:
  filtrar por contexto operacional, ordenar por inicio/fim/logs, paginar, navegar para automacao, cliente, host e detalhe da run.
- graficos:
  distribuicao por status, volume por dia e distribuicao por hora.

### 11. Historico de Execucoes por Automacao

- rota: `/automations/:automationId/runs`
- arquivo: `remote_dashboard/frontend/src/pages/RunsPage.jsx`
- objetivo:
  focar o historico em uma automacao especifica.
- funcionalidades:
  reutiliza a mesma tela de runs, mas com contexto de automacao e sem filtros globais de cliente/host.

### 12. Historico de Execucoes por Instancia

- rota: `/instances/:instanceId/runs`
- arquivo: `remote_dashboard/frontend/src/pages/RunsPage.jsx`
- objetivo:
  listar runs de uma instancia especifica.
- funcionalidades:
  mesma base da tela de runs, agora em escopo de instancia.

### 13. Detalhe de Execucao

- rota: `/runs/:runId`
- arquivo: `remote_dashboard/frontend/src/pages/RunDetailPage.jsx`
- objetivo:
  inspecionar profundamente uma execucao, seus logs e seus e-mails.
- blocos principais:
  cabecalho operacional da run, filtros de log, graficos de metricas, auditoria de e-mails, reconstrucao da execucao e visualizacao textual de logs.
- funcionalidades de logs:
  busca textual, filtro por nivel, ordenacao asc/desc, expansao ou recolhimento de contexto, paginacao, navegacao por grafico temporal, leitura de `context` e `extra`.
- funcionalidades de execucao:
  alternar entre modo `Logs` e modo `Execucao`, onde o modo `Execucao` usa `ExecutionView` para reconstruir o fluxo a partir de call chains e relacoes entre spans/logs.
- funcionalidades de e-mail:
  listar eventos de e-mail, abrir detalhe do e-mail em modal e baixar ou visualizar anexos.

### 14. Detalhe de E-mail

- entrada:
  modal dentro da tela de run
- arquivos:
  `remote_dashboard/frontend/src/components/EmailCard.jsx`
  `remote_dashboard/frontend/src/components/EmailDetailModal.jsx`
- objetivo:
  apresentar metadados do e-mail e anexos capturados pela automacao.
- funcionalidades:
  visualizar remetente, destinatarios, assunto, corpo, anexos, tipo de arquivo detectado e links de `download`/`preview`.

### 15. Reconstrucao de Execucao

- entrada:
  secao interna da tela `/runs/:runId`
- arquivos:
  `remote_dashboard/frontend/src/components/ExecutionView.jsx`
  `remote_dashboard/frontend/src/components/ExecutionTimeline.jsx`
  `remote_dashboard/frontend/src/components/ExecutionTimelineList.jsx`
  `remote_dashboard/frontend/src/components/SpanTreeView.jsx`
- objetivo:
  oferecer uma leitura mais semantica da execucao do que a simples lista de logs.
- funcionalidades:
  reconstruir fluxo temporal, spans, call chains, agrupamentos e relacao entre eventos de execucao.
- valor funcional:
  ajuda a entender ordem, encadeamento e sobreposicao de passos da automacao.

### 16. Agendamentos

- rota: `/schedules`
- arquivo: `remote_dashboard/frontend/src/pages/SchedulesPage.jsx`
- objetivo:
  administrar recorrencias e observar calendario de execucao.
- elementos principais:
  CTA de `Iniciar Agora`, CTA de `Novo Agendamento`, barra de status de agentes, calendario mensal/semanal e tabela de agendamentos.
- funcionalidades:
  navegar no calendario, alternar visao mes/semana, ativar/desativar schedule, excluir schedule, visualizar ocorrencias concretas no calendario.
- barra de agentes:
  mostra quais hosts possuem agent conectado no momento.

### 17. Criacao de Agendamento

- entrada:
  modal `Novo Agendamento`
- arquivo: `remote_dashboard/frontend/src/components/ScheduleModal.jsx`
- objetivo:
  criar recorrencias para uma instancia de automacao.
- funcionalidades:
  escolher automacao, cliente, maquina e instancia; definir script; preencher argumentos estruturados ou texto livre; selecionar modo de execucao `parallel` ou `sequential`; configurar recorrencia diaria, dias uteis, dias especificos, mensal ou anual; definir horario; marcar schedule como habilitado.
- comportamento relevante:
  privilegia instancias com agent conectado e tenta auto-selecionar cliente/host quando houver apenas uma opcao disponivel.

### 18. Iniciar Agora

- entrada:
  modal `Iniciar Agora`
- arquivo: `remote_dashboard/frontend/src/components/ScheduleModal.jsx`
- objetivo:
  disparar execucao imediata para uma instancia.
- funcionalidades:
  mesma selecao de automacao/cliente/host/instancia, preenchimento de script e argumentos, definicao de modo de execucao e envio para `/dashboard-api/commands/run-now`.

### 19. Comandos

- rota: `/commands`
- arquivo: `remote_dashboard/frontend/src/pages/CommandsPage.jsx`
- objetivo:
  acompanhar o historico de comandos disparados manualmente ou por scheduler.
- elementos principais:
  busca textual, filtro de status e tabela de comandos.
- funcionalidades:
  ver origem do comando, acompanhar status, cancelar comandos `acked` ou `running`, abrir run associada quando existir.
- statuses tratados:
  `pending`, `acked`, `running`, `completed`, `failed`, `cancelled`, `expired`.

### 20. Meu Perfil

- rota: `/profile`
- arquivo: `remote_dashboard/frontend/src/pages/ProfilePage.jsx`
- objetivo:
  expor informacoes do usuario autenticado e permitir troca de senha.
- funcionalidades:
  visualizar nome, email, papel, permissoes e alterar senha com validacao de confirmacao.

### 21. Administracao de Usuarios

- rota: `/admin/users`
- arquivo: `remote_dashboard/frontend/src/pages/AdminUsersPage.jsx`
- objetivo:
  administrar usuarios internos do painel.
- acesso:
  somente `admin`; usuarios nao-admin sao redirecionados para `/`.
- funcionalidades:
  listar usuarios, criar usuario, exibir senha temporaria, ativar/inativar conta, editar permissoes, restringir automacoes permitidas, resetar senha e revogar sessoes.
- modais envolvidos:
  `CreateUserModal`, `EditAccessModal` e `TempPasswordModal`.

### 22. AI Assistant

- entrada:
  widget persistente em todas as telas autenticadas
- arquivo: `remote_dashboard/frontend/src/components/AiChatWidget.jsx`
- objetivo:
  fornecer assistencia conversacional contextual ao usuario do dashboard.
- funcionalidades:
  painel lateral redimensionavel, historico de mensagens, streaming SSE, exibicao de raciocinio, exibicao de tool calls, navegacao por links internos, copia de respostas e fluxo de `ask_continue` quando muitas consultas sao feitas.
- backend consumido:
  `/dashboard-api/ai/chat` e `/dashboard-api/ai/chat/continue`.
- percepcao funcional:
  e um canal embutido para ajuda operacional e consulta contextual ao estado atual da pagina.

### 23. Pagina nao encontrada

- rota: `/404`
- arquivo: `remote_dashboard/frontend/src/pages/NotFoundPage.jsx`
- objetivo:
  tratar rotas inexistentes.
- funcionalidades:
  informar erro de navegacao e oferecer retorno para a visao geral.

## Componentes estruturais relevantes

Componentes base recorrentes:

- `PageHeader`
  padroniza titulo, subtitulo, acoes e extras.
- `SectionCard`
  organiza blocos funcionais.
- `DataTable`
  tabela reutilizavel para hosts, clientes, runs, comandos e schedules.
- `LoadingState`, `ErrorState`, `EmptyState`, `FeedbackToast`
  padrao de estados de tela e feedback.
- `BusyButton`
  botao com estado de processamento.
- `StatusBadge`
  badge de status para runs.

## Endpoints efetivamente consumidos pela UI

Conforme `remote_dashboard/frontend/src/lib/api.js`, o frontend usa:

- autenticacao:
  `/dashboard-api/auth/login`
  `/dashboard-api/auth/refresh`
  `/dashboard-api/auth/logout`
  `/dashboard-api/auth/me`
  `/dashboard-api/auth/change-password`
- observabilidade:
  `/dashboard-api/health`
  `/dashboard-api/insights/hosts*`
  `/dashboard-api/insights/automations*`
  `/dashboard-api/insights/clients*`
  `/dashboard-api/insights/runs*`
  `/dashboard-api/insights/emails/*/attachments/*`
- controle remoto:
  `/dashboard-api/schedules*`
  `/dashboard-api/commands*`
  `/dashboard-api/instances/:id/args`
  `/dashboard-api/agent/status`
- administracao:
  `/dashboard-api/admin/users*`
- AI assistant:
  `/dashboard-api/ai/chat`
  `/dashboard-api/ai/chat/continue`

## Fluxos funcionais mais importantes

### Observabilidade

- o usuario acompanha saude operacional na visao geral
- aprofunda por inventario, cliente, automacao ou execucao
- chega ao detalhe da run para logs, e-mails e reconstrucao da execucao

### Controle remoto

- o usuario pode criar agendamento recorrente
- ou disparar `Iniciar Agora`
- a API cria `commands`
- o agent conectado recebe execucao ou cancelamento
- a tela `Comandos` acompanha esse ciclo

### Governanca de acesso

- autenticacao por token + refresh cookie
- perfil para senha e leitura de permissao
- administracao para criacao de usuarios, reset de senha e escopo de acesso por automacao

## Lacunas e pontos de atencao

- `AutomationDetailPage.jsx` existe, mas o arquivo tem apenas um placeholder; o detalhe real da automacao vive em `AutomationModal.jsx`.
- o link da tela de detalhe do cliente para `/automations/:automation_id` nao corresponde a uma rota declarada no `App.jsx`.
- a documentacao interna atual (`frontend-dashboard.md`) lista as rotas principais, mas nao documenta em profundidade os modais secundarios, o widget de IA e as regras de permissao.
- o menu lateral nao expõe atalhos para `/profile` nem `/admin/users`; esses acessos aparecem por fluxo secundario.

## Arquivos-chave para futuras leituras

- `remote_dashboard/frontend/src/App.jsx`
- `remote_dashboard/frontend/src/layout/PanelLayout.jsx`
- `remote_dashboard/frontend/src/lib/api.js`
- `remote_dashboard/frontend/src/pages/DashboardPage.jsx`
- `remote_dashboard/frontend/src/pages/RunsPage.jsx`
- `remote_dashboard/frontend/src/pages/RunDetailPage.jsx`
- `remote_dashboard/frontend/src/pages/SchedulesPage.jsx`
- `remote_dashboard/frontend/src/pages/CommandsPage.jsx`
- `remote_dashboard/frontend/src/components/AutomationModal.jsx`
- `remote_dashboard/frontend/src/components/ScheduleModal.jsx`
- `remote_dashboard/frontend/src/components/AiChatWidget.jsx`
