import { Users } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../lib/auth';
import { panelNavigation } from './panelNavigation';

function Sidebar({ onNavigate }) {
  const { user } = useAuth();
  return (
    <aside className="flex h-screen w-72 shrink-0 flex-col border-r border-app-border bg-app-elevated/95 backdrop-blur-xl">
      <div className="flex flex-col items-center gap-3 bg-[#2b114a] px-6 py-6">
        {/* TODO: replace with branding logo — reads from ARGUS_LOGO_URL when set */}
        <span className="text-xl font-bold text-white tracking-wide">Argus</span>
        <p className="text-center text-[11px] font-medium uppercase tracking-[0.14em] text-white/60">
          Monitoramento de execucoes RPA
        </p>
      </div>
      <div className="flex-1 flex flex-col p-4 overflow-hidden">

      <nav data-tour="sidebar-nav" className="flex-1 space-y-5 overflow-y-auto pr-1">
        {panelNavigation.map((section) => (
          <div key={section.group}>
            <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-app-muted/80">
              {section.group}
            </p>
            <div className="space-y-1">
              {section.items.map((item) => {
                const Icon = item.icon;
                const tourId = { '/': 'nav-dashboard', '/automations': 'nav-automations', '/runs': 'nav-runs', '/schedules': 'nav-schedules' }[item.to];
                return (
                  <NavLink
                    key={`${section.group}-${item.to}-${item.label}`}
                    to={item.to}
                    onClick={onNavigate}
                    {...(tourId ? { 'data-tour': tourId } : {})}
                    className={({ isActive }) =>
                      `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                        isActive
                          ? 'bg-app-primary/20 text-app-accent shadow-sm'
                          : 'text-app-muted hover:bg-app-primary/10 hover:text-app-text'
                      }`
                    }
                  >
                    <Icon className="h-4 w-4" />
                    <span>{item.label}</span>
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>
      {user?.role === 'admin' && (
        <div className="border-t border-app-border p-4">
          <p className="mb-2 px-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-app-muted/80">
            Admin
          </p>
          <NavLink
            to="/admin/users"
            onClick={onNavigate}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                isActive
                  ? 'bg-app-primary/20 text-app-accent shadow-sm'
                  : 'text-app-muted hover:bg-app-primary/10 hover:text-app-text'
              }`
            }
          >
            <Users className="h-4 w-4" />
            <span>Usuarios</span>
          </NavLink>
        </div>
      )}
      </div>
    </aside>
  );
}

export default Sidebar;
