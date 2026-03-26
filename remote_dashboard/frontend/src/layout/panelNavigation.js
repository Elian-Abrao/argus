import {
  Bot,
  Building2,
  Calendar,
  HardDrive,
  LayoutDashboard,
  Network,
} from 'lucide-react';

export const panelNavigation = [
  {
    group: 'Operacao',
    items: [
      {
        label: 'Visao Geral',
        to: '/',
        icon: LayoutDashboard,
      },
    ],
  },
  {
    group: 'Inventario',
    items: [
      {
        label: 'Maquinas',
        to: '/hosts',
        icon: HardDrive,
      },
      {
        label: 'Robos',
        to: '/automations',
        icon: Bot,
      },
      {
        label: 'Clientes',
        to: '/clients',
        icon: Building2,
      },
    ],
  },
  {
    group: 'Rastreamento',
    items: [
      {
        label: 'Execucoes',
        to: '/runs',
        icon: Network,
      },
    ],
  },
  {
    group: 'Controle',
    items: [
      {
        label: 'Agendamentos',
        to: '/schedules',
        icon: Calendar,
      },
    ],
  },
];
