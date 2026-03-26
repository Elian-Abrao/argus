import { LogOut, Menu, RefreshCw, X } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { Link, Outlet, useLocation } from 'react-router-dom';
import BusyButton from '../components/BusyButton';
import AiChatWidget from '../components/AiChatWidget';
import Sidebar from './Sidebar';
import { useAuth } from '../lib/auth';
import { isOnboardingCompleted, startOnboardingTour } from '../lib/onboarding';

const breadcrumbRules = [
  { test: (path) => path === '/', label: 'Visao Geral' },
  { test: (path) => path.startsWith('/hosts/'), label: 'Maquinas / Detalhe' },
  { test: (path) => path === '/hosts', label: 'Maquinas' },
  { test: (path) => path.startsWith('/automations/') && path.endsWith('/runs'), label: 'Robos / Execucoes' },
  { test: (path) => path.startsWith('/automations/'), label: 'Robos / Detalhe' },
  { test: (path) => path === '/automations', label: 'Robos' },
  { test: (path) => path.startsWith('/instances/') && path.endsWith('/runs'), label: 'Instancia / Execucoes' },
  { test: (path) => path.startsWith('/clients/'), label: 'Clientes / Detalhe' },
  { test: (path) => path === '/clients', label: 'Clientes' },
  { test: (path) => path === '/runs', label: 'Execucoes' },
  { test: (path) => path.startsWith('/runs/'), label: 'Execucao / Logs' },
  { test: (path) => path === '/schedules', label: 'Agendamentos' },
  { test: (path) => path === '/profile', label: 'Meu Perfil' },
];

function PanelLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [headerAction, setHeaderAction] = useState(null);
  const location = useLocation();
  const { user, logout } = useAuth();

  // Onboarding tour — auto-start on first visit
  useEffect(() => {
    if (!user || isOnboardingCompleted()) return;
    // Small delay to ensure DOM is rendered
    const timer = setTimeout(() => startOnboardingTour(), 800);
    return () => clearTimeout(timer);
  }, [user]);

  const breadcrumb = useMemo(() => {
    const found = breadcrumbRules.find((item) => item.test(location.pathname));
    return found ? found.label : 'Painel';
  }, [location.pathname]);

  return (
    <>
    <div className="min-h-screen bg-app-bg text-app-text">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,_rgba(184,147,255,0.42),_transparent_54%),radial-gradient(circle_at_82%_14%,_rgba(130,10,209,0.18),_transparent_40%)]" />

      <div className="min-h-screen lg:pl-72">
        <div className="hidden lg:fixed lg:inset-y-0 lg:left-0 lg:z-30 lg:block">
          <Sidebar />
        </div>

        {menuOpen ? (
          <div className="fixed inset-0 z-50 lg:hidden">
            <button
              type="button"
              aria-label="Fechar menu"
              className="absolute inset-0 bg-[#2b114a]/30"
              onClick={() => setMenuOpen(false)}
            />
            <div className="relative h-full w-72">
              <Sidebar onNavigate={() => setMenuOpen(false)} />
            </div>
          </div>
        ) : null}

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 border-b border-app-border bg-app-elevated/75 px-4 py-3 backdrop-blur-xl lg:px-8">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <button
                  type="button"
                  className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-app-border bg-app-surface/80 text-app-text lg:hidden"
                  onClick={() => setMenuOpen((previous) => !previous)}
                  aria-label="Alternar menu"
                >
                  {menuOpen ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
                </button>
                <div>
                  <p className="text-xs uppercase tracking-[0.14em] text-app-muted">Argus</p>
                  <p className="text-sm font-semibold text-app-text">{breadcrumb}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {headerAction ? (
                  <BusyButton
                    busy={headerAction.busy}
                    type="button"
                    onClick={headerAction.onClick}
                    className="!border-app-border !bg-app-surface/80 !px-4 !py-2 !text-xs !font-bold !text-app-text hover:!bg-app-primary/10 hover:!text-app-text"
                  >
                    <RefreshCw className="h-3.5 w-3.5" /> {headerAction.label || 'Atualizar'}
                  </BusyButton>
                ) : null}
                {user && (
                  <div data-tour="header-user" className="flex items-center gap-2">
                    <Link to="/profile" className="hidden sm:block text-right hover:opacity-80 transition">
                      <p className="text-xs font-medium text-app-text leading-tight">{user.full_name}</p>
                      <p className="text-[10px] text-app-muted capitalize">{user.role}</p>
                    </Link>
                    <button
                      type="button"
                      onClick={logout}
                      title="Sair"
                      className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-app-border bg-app-surface/80 text-app-muted hover:text-red-400 hover:border-red-400/40 transition"
                    >
                      <LogOut className="h-3.5 w-3.5" />
                    </button>
                  </div>
                )}
              </div>
            </div>
          </header>

          <main className="flex-1 px-4 py-5 lg:px-8 lg:py-7">
            <Outlet context={{ setHeaderAction }} />
          </main>
        </div>
      </div>
    </div>
    <AiChatWidget />
    </>
  );
}

export default PanelLayout;
