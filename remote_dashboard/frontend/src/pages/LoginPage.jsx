import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../lib/auth';

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
      navigate('/', { replace: true });
    } catch (err) {
      setError(err.message || 'Falha ao autenticar');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-app-bg text-app-text flex items-center justify-center">
      <div className="pointer-events-none fixed inset-0 -z-10 bg-[radial-gradient(circle_at_top_left,_rgba(184,147,255,0.42),_transparent_54%),radial-gradient(circle_at_82%_14%,_rgba(130,10,209,0.18),_transparent_40%)]" />

      <div className="w-full max-w-sm">
        <div className="rounded-2xl border border-app-border bg-app-elevated/95 shadow-xl backdrop-blur-xl overflow-hidden">
          <div className="flex flex-col items-center gap-2 bg-[#2b114a] px-6 py-8">
            {/* TODO: replace with branding logo — reads from ARGUS_LOGO_URL when set */}
            <span className="text-2xl font-bold text-white tracking-wide">Argus</span>
            <p className="text-center text-[11px] font-medium uppercase tracking-[0.14em] text-white/60">
              Monitoramento de execucoes RPA
            </p>
          </div>

          <div className="px-6 py-8">
            <h1 className="mb-6 text-center text-lg font-semibold text-app-text">Entrar</h1>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="mb-1.5 block text-xs font-medium text-app-muted" htmlFor="email">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  required
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full rounded-xl border border-app-border bg-app-surface px-3 py-2.5 text-sm text-app-text placeholder-app-muted/50 outline-none focus:border-app-accent focus:ring-1 focus:ring-app-accent"
                  placeholder="seu@email.com"
                />
              </div>

              <div>
                <label className="mb-1.5 block text-xs font-medium text-app-muted" htmlFor="password">
                  Senha
                </label>
                <input
                  id="password"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full rounded-xl border border-app-border bg-app-surface px-3 py-2.5 text-sm text-app-text placeholder-app-muted/50 outline-none focus:border-app-accent focus:ring-1 focus:ring-app-accent"
                  placeholder="••••••••••"
                />
              </div>

              {error && (
                <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="mt-2 w-full rounded-xl bg-app-accent px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-app-accent/90 disabled:opacity-50"
              >
                {loading ? 'Entrando...' : 'Entrar'}
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
