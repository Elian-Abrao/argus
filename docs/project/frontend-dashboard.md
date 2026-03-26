# Frontend Dashboard

## Escopo

O `remote_dashboard/` e um servico FastAPI enxuto que entrega uma SPA React para observabilidade e controle operacional.

## Arquitetura

### Servidor do dashboard

- `remote_dashboard/main.py`
  - serve `frontend/dist`
  - publica `/assets/*`
  - faz fallback de rotas para `index.html`
  - aplica `ForwardedHeadersMiddleware`

### Proxy same-origin

- `remote_dashboard/api_proxy.py`
  - expõe `/dashboard-api/*`
  - encaminha para `remote_api`
  - evita CORS no frontend

### Frontend React

- stack:
  - React
  - Vite
  - React Router
  - Tailwind CSS
  - Recharts
  - Lucide

## Estrutura do frontend

- `frontend/src/App.jsx`
  - define rotas
- `frontend/src/layout/`
  - shell e navegacao
- `frontend/src/pages/`
  - uma tela por rota
- `frontend/src/components/`
  - componentes reutilizaveis
- `frontend/src/lib/api.js`
  - cliente HTTP unico
- `frontend/src/lib/format.js`
  - utilitarios de formatacao

## Padrao de estado

As paginas usam estado local com:

- `useState`
- `useEffect`
- `useMemo`

Padrao recorrente:

- `loading`
- `refreshing`
- `saving`
- `error`
- `data`
- `feedback`

Nao ha store global.

## Rotas da SPA

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
- `/404`

## Paginas principais

### Dashboard

- `DashboardPage.jsx`
- overview operacional
- graficos de status/volume
- timeline de execucoes
- checklist de agendamentos

### Inventario

- `HostsPage.jsx`
- `HostDetailPage.jsx`
- `AutomationsPage.jsx`
- `ClientsPage.jsx`
- `ClientDetailPage.jsx`

### Execucoes

- `RunsPage.jsx`
- `RunDetailPage.jsx`

### Controle remoto

- `SchedulesPage.jsx`
- `CommandsPage.jsx`
- `ScheduleModal.jsx`
- `InstanceArgsModal.jsx`

## Componentes compartilhados mais importantes

### Estrutura

- `PanelLayout.jsx`
- `Sidebar.jsx`
- `panelNavigation.js`
- `PageHeader.jsx`
- `SectionCard.jsx`

### Estados de tela

- `LoadingState.jsx`
- `ErrorState.jsx`
- `EmptyState.jsx`
- `FeedbackToast.jsx`
- `BusyButton.jsx`

### Operacao e observabilidade

- `ExecutionTimeline.jsx`
- `ExecutionTimelineList.jsx`
- `ExecutionView.jsx`
- `SpanTreeView.jsx`
- `StatusBadge.jsx`
- `ScheduleChecklist.jsx`

### Dados e formulários

- `DataTable.jsx`
- `FilterBar.jsx`
- `AutomationModal.jsx`
- `ScheduleModal.jsx`
- `EmailCard.jsx`
- `EmailDetailModal.jsx`

## Cliente HTTP

- `frontend/src/lib/api.js`

### Regras

- base fixa: `/dashboard-api`
- `request()` centraliza `fetch`, `credentials`, parsing e mapeamento de erros
- toda chamada da UI passa por esse arquivo

### Endpoints proxied consumidos pela UI

- `/dashboard-api/health`
- `/dashboard-api/insights/*`
- `/dashboard-api/schedules*`
- `/dashboard-api/commands*`
- `/dashboard-api/agent/status`
- `/dashboard-api/agent/identify`
- `/dashboard-api/instances/:id/args`

## Particularidades de dominio

- o dashboard trabalha com datas locais e envia datas em formato local sem conversao UTC
- `getRunLogs()` traduz `sort` para `order`
- `getDashboardOverviewData()` monta um agregado composto em paralelo
- o checklist de schedules cruza calendario, commands e timeline

## Pontos de atencao

- `AutomationDetailPage.jsx` existe, mas o detalhe operacional real esta em `AutomationModal.jsx`
- o bundle de producao esta grande e o build aponta warning de chunk
- ha forte acoplamento com payloads agregados do backend
