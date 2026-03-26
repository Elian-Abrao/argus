import { GraduationCap, KeyRound, Mail, ShieldCheck, User } from 'lucide-react';
import { useState } from 'react';
import { changePassword } from '../lib/api';
import { useAuth } from '../lib/auth';
import { resetOnboarding, startOnboardingTour } from '../lib/onboarding';

export default function ProfilePage() {
  const { user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  async function handleChangePassword(e) {
    e.preventDefault();
    setError('');
    setSuccess('');

    if (newPassword !== confirmPassword) {
      setError('As senhas nao coincidem');
      return;
    }

    setLoading(true);
    try {
      await changePassword({ current_password: currentPassword, new_password: newPassword });
      setSuccess('Senha alterada com sucesso');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setError(err.message || 'Erro ao alterar senha');
    } finally {
      setLoading(false);
    }
  }

  if (!user) return null;

  const permissionLabels = {
    view_all: 'Visualizar tudo',
    run_automations: 'Iniciar/parar automacoes',
    configure_args: 'Configurar argumentos',
  };

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <div className="rounded-2xl border border-app-border bg-app-elevated/95 p-6 shadow-xl backdrop-blur-xl">
        <h2 className="mb-5 text-base font-semibold text-app-text">Meu perfil</h2>

        <div className="space-y-4">
          <div className="flex items-center gap-3 rounded-xl border border-app-border bg-app-surface px-4 py-3">
            <User className="h-4 w-4 text-app-muted" />
            <div className="min-w-0 flex-1">
              <p className="text-[11px] text-app-muted">Nome</p>
              <p className="text-sm font-medium text-app-text">{user.full_name}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-app-border bg-app-surface px-4 py-3">
            <Mail className="h-4 w-4 text-app-muted" />
            <div className="min-w-0 flex-1">
              <p className="text-[11px] text-app-muted">Email</p>
              <p className="text-sm font-medium text-app-text">{user.email}</p>
            </div>
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-app-border bg-app-surface px-4 py-3">
            <ShieldCheck className="h-4 w-4 text-app-muted" />
            <div className="min-w-0 flex-1">
              <p className="text-[11px] text-app-muted">Funcao</p>
              <p className="text-sm font-medium text-app-text capitalize">{user.role}</p>
            </div>
          </div>

          {user.permissions && user.permissions.length > 0 && (
            <div className="rounded-xl border border-app-border bg-app-surface px-4 py-3">
              <p className="mb-2 text-[11px] text-app-muted">Permissoes</p>
              <div className="flex flex-wrap gap-1.5">
                {user.permissions.map((perm) => (
                  <span
                    key={perm}
                    className="rounded-lg bg-app-accent/15 px-2.5 py-1 text-[11px] font-medium text-app-accent"
                  >
                    {permissionLabels[perm] || perm}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-app-border bg-app-elevated/95 p-6 shadow-xl backdrop-blur-xl">
        <div className="mb-3 flex items-center gap-2">
          <GraduationCap className="h-4 w-4 text-app-muted" />
          <h2 className="text-base font-semibold text-app-text">Tour guiado</h2>
        </div>
        <p className="mb-4 text-xs text-app-muted leading-relaxed">
          Reveja as áreas principais do painel com um passo a passo interativo.
        </p>
        <button
          type="button"
          onClick={() => { resetOnboarding(); startOnboardingTour(); }}
          className="rounded-xl border border-app-accent/30 bg-app-accent/10 px-4 py-2.5 text-sm font-medium text-app-accent transition hover:bg-app-accent/20"
        >
          Refazer tour do painel
        </button>
      </div>

      <div className="rounded-2xl border border-app-border bg-app-elevated/95 p-6 shadow-xl backdrop-blur-xl">
        <div className="mb-5 flex items-center gap-2">
          <KeyRound className="h-4 w-4 text-app-muted" />
          <h2 className="text-base font-semibold text-app-text">Alterar senha</h2>
        </div>

        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label className="mb-1.5 block text-xs font-medium text-app-muted" htmlFor="currentPassword">
              Senha atual
            </label>
            <input
              id="currentPassword"
              type="password"
              required
              autoComplete="current-password"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full rounded-xl border border-app-border bg-app-surface px-3 py-2.5 text-sm text-app-text placeholder-app-muted/50 outline-none focus:border-app-accent focus:ring-1 focus:ring-app-accent"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-app-muted" htmlFor="newPassword">
              Nova senha
            </label>
            <input
              id="newPassword"
              type="password"
              required
              autoComplete="new-password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full rounded-xl border border-app-border bg-app-surface px-3 py-2.5 text-sm text-app-text placeholder-app-muted/50 outline-none focus:border-app-accent focus:ring-1 focus:ring-app-accent"
            />
          </div>

          <div>
            <label className="mb-1.5 block text-xs font-medium text-app-muted" htmlFor="confirmPassword">
              Confirmar nova senha
            </label>
            <input
              id="confirmPassword"
              type="password"
              required
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="w-full rounded-xl border border-app-border bg-app-surface px-3 py-2.5 text-sm text-app-text placeholder-app-muted/50 outline-none focus:border-app-accent focus:ring-1 focus:ring-app-accent"
            />
          </div>

          {error && (
            <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
              {error}
            </p>
          )}

          {success && (
            <p className="rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-2 text-xs text-green-400">
              {success}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-app-accent px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-app-accent/90 disabled:opacity-50"
          >
            {loading ? 'Alterando...' : 'Alterar senha'}
          </button>
        </form>
      </div>
    </div>
  );
}
