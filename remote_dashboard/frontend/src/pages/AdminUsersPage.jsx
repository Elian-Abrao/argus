import { KeyRound, Plus, RefreshCw, ShieldCheck, Trash2, UserCheck, UserX } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  adminCreateUser,
  adminListUsers,
  adminResetPassword,
  adminRevokeSessions,
  adminSetUserAccess,
  adminUpdateUser,
  getAutomations,
  getClients,
} from '../lib/api';
import { useAuth } from '../lib/auth';

const PERMISSIONS = [
  { value: 'view_all', label: 'Visualizar tudo' },
  { value: 'run_automations', label: 'Iniciar/parar automacoes' },
  { value: 'configure_args', label: 'Configurar argumentos' },
];

function TempPasswordModal({ data, onClose }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl border border-app-border bg-app-elevated p-6 shadow-xl">
        <h2 className="mb-1 text-base font-semibold text-app-text">Usuario criado</h2>
        <p className="mb-4 text-xs text-app-muted">
          Compartilhe a senha tempor&#225;ria com <strong>{data.email}</strong>. Ela n&#227;o ser&#225;
          exibida novamente.
        </p>
        <div className="rounded-xl border border-app-border bg-app-surface px-4 py-3 font-mono text-sm text-app-accent">
          {data.temporary_password}
        </div>
        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full rounded-xl bg-app-accent px-4 py-2.5 text-sm font-semibold text-white hover:bg-app-accent/90"
        >
          Fechar
        </button>
      </div>
    </div>
  );
}

function CreateUserModal({ onClose, onCreated }) {
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('user');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const result = await adminCreateUser({ email, full_name: fullName, role });
      onCreated(result);
    } catch (err) {
      setError(err.message || 'Erro ao criar usuario');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl border border-app-border bg-app-elevated p-6 shadow-xl">
        <h2 className="mb-4 text-base font-semibold text-app-text">Novo usuario</h2>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="mb-1 block text-xs text-app-muted">Nome completo</label>
            <input
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="w-full rounded-xl border border-app-border bg-app-surface px-3 py-2 text-sm text-app-text outline-none focus:border-app-accent"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-app-muted">Email</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-xl border border-app-border bg-app-surface px-3 py-2 text-sm text-app-text outline-none focus:border-app-accent"
            />
          </div>
          <div>
            <label className="mb-1 block text-xs text-app-muted">Perfil</label>
            <select
              value={role}
              onChange={(e) => setRole(e.target.value)}
              className="w-full rounded-xl border border-app-border bg-app-surface px-3 py-2 text-sm text-app-text outline-none focus:border-app-accent"
            >
              <option value="user">Operador</option>
              <option value="admin">Administrador</option>
            </select>
          </div>
          {error && (
            <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
              {error}
            </p>
          )}
          <div className="flex gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-xl border border-app-border px-4 py-2 text-sm text-app-muted hover:text-app-text"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={loading}
              className="flex-1 rounded-xl bg-app-accent px-4 py-2 text-sm font-semibold text-white hover:bg-app-accent/90 disabled:opacity-50"
            >
              {loading ? 'Criando...' : 'Criar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function EditAccessModal({ user, onClose, onSaved }) {
  const [permissions, setPermissions] = useState(user.permissions || []);
  const [selectedAutomations, setSelectedAutomations] = useState(user.automation_ids || []);
  const [selectedClients, setSelectedClients] = useState(user.client_ids || []);
  const [isActive, setIsActive] = useState(user.is_active);
  const [automations, setAutomations] = useState([]);
  const [clients, setClients] = useState([]);
  const [automationsLoading, setAutomationsLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [clientSearch, setClientSearch] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const [autoData, clientData] = await Promise.all([
          getAutomations({ limit: 500 }),
          getClients({ limit: 500 }),
        ]);
        setAutomations(autoData.items || []);
        setClients(clientData.items || []);
      } catch {
        setAutomations([]);
        setClients([]);
      } finally {
        setAutomationsLoading(false);
      }
    })();
  }, []);

  function togglePerm(perm) {
    setPermissions((prev) =>
      prev.includes(perm) ? prev.filter((p) => p !== perm) : [...prev, perm]
    );
  }

  function toggleAutomation(id) {
    setSelectedAutomations((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id]
    );
  }

  function toggleClient(id) {
    setSelectedClients((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id]
    );
  }

  const filteredClients = clients.filter((c) => {
    if (!clientSearch) return true;
    const term = clientSearch.toLowerCase();
    return (
      (c.name || '').toLowerCase().includes(term) ||
      (c.external_code || '').toLowerCase().includes(term)
    );
  });

  const filteredAutomations = automations.filter((a) => {
    if (!search) return true;
    const term = search.toLowerCase();
    return (
      (a.code || '').toLowerCase().includes(term) ||
      (a.name || '').toLowerCase().includes(term)
    );
  });

  async function handleSave() {
    setError('');
    setLoading(true);
    try {
      await adminUpdateUser(user.id, { is_active: isActive });
      if (user.role !== 'admin') {
        await adminSetUserAccess(user.id, { permissions, automation_ids: selectedAutomations, client_ids: selectedClients });
      }
      onSaved();
    } catch (err) {
      setError(err.message || 'Erro ao salvar');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl border border-app-border bg-app-elevated p-6 shadow-xl max-h-[85vh] flex flex-col">
        <h2 className="mb-1 text-base font-semibold text-app-text">Editar acesso</h2>
        <p className="mb-4 text-xs text-app-muted">{user.full_name} &bull; {user.email}</p>

        <div className="space-y-4 overflow-y-auto flex-1 min-h-0 pr-1">
          <div className="flex items-center justify-between rounded-xl border border-app-border bg-app-surface px-4 py-3">
            <span className="text-sm text-app-text">Conta ativa</span>
            <button
              type="button"
              onClick={() => setIsActive((v) => !v)}
              className={`relative inline-flex h-5 w-9 items-center rounded-full transition ${
                isActive ? 'bg-app-accent' : 'bg-app-border'
              }`}
            >
              <span
                className={`inline-block h-3.5 w-3.5 rounded-full bg-white transition-transform ${
                  isActive ? 'translate-x-4' : 'translate-x-1'
                }`}
              />
            </button>
          </div>

          {user.role !== 'admin' && (
            <>
              <div>
                <p className="mb-2 text-xs font-medium text-app-muted">Permissoes</p>
                <div className="space-y-2">
                  {PERMISSIONS.map((p) => (
                    <label
                      key={p.value}
                      className="flex cursor-pointer items-center gap-3 rounded-xl border border-app-border bg-app-surface px-4 py-2.5"
                    >
                      <input
                        type="checkbox"
                        checked={permissions.includes(p.value)}
                        onChange={() => togglePerm(p.value)}
                        className="accent-app-accent"
                      />
                      <span className="text-sm text-app-text">{p.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {!permissions.includes('view_all') && (
                <>
                <div>
                  <p className="mb-2 text-xs font-medium text-app-muted">
                    Clientes permitidos
                    <span className="ml-1 text-app-accent font-bold">
                      ({selectedClients.length})
                    </span>
                  </p>
                  <input
                    type="text"
                    placeholder="Buscar cliente..."
                    value={clientSearch}
                    onChange={(e) => setClientSearch(e.target.value)}
                    className="mb-2 w-full rounded-xl border border-app-border bg-app-surface px-3 py-2 text-sm text-app-text outline-none focus:border-app-accent"
                  />
                  {automationsLoading ? (
                    <div className="flex justify-center py-4">
                      <div className="h-5 w-5 animate-spin rounded-full border-2 border-app-accent border-t-transparent" />
                    </div>
                  ) : (
                    <div className="max-h-40 space-y-1 overflow-y-auto rounded-xl border border-app-border bg-app-surface p-2">
                      {filteredClients.length === 0 ? (
                        <p className="py-2 text-center text-xs text-app-muted">Nenhum cliente encontrado</p>
                      ) : (
                        filteredClients.map((c) => (
                          <label
                            key={c.id}
                            className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 hover:bg-app-elevated/60 transition"
                          >
                            <input
                              type="checkbox"
                              checked={selectedClients.includes(c.id)}
                              onChange={() => toggleClient(c.id)}
                              className="accent-app-accent"
                            />
                            <div className="min-w-0 flex-1">
                              <span className="block truncate text-sm text-app-text">{c.name}</span>
                              {c.external_code && (
                                <span className="block truncate text-[11px] text-app-muted">{c.external_code}</span>
                              )}
                            </div>
                          </label>
                        ))
                      )}
                    </div>
                  )}
                  <p className="mt-1 text-[10px] text-app-muted">Todas as automacoes do cliente ficam disponiveis</p>
                </div>

                <div>
                  <p className="mb-2 text-xs font-medium text-app-muted">
                    Automacoes avulsas
                    <span className="ml-1 text-app-accent font-bold">
                      ({selectedAutomations.length})
                    </span>
                  </p>
                  <input
                    type="text"
                    placeholder="Buscar automacao..."
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="mb-2 w-full rounded-xl border border-app-border bg-app-surface px-3 py-2 text-sm text-app-text outline-none focus:border-app-accent"
                  />
                  {automationsLoading ? (
                    <div className="flex justify-center py-4">
                      <div className="h-5 w-5 animate-spin rounded-full border-2 border-app-accent border-t-transparent" />
                    </div>
                  ) : (
                    <div className="max-h-52 space-y-1 overflow-y-auto rounded-xl border border-app-border bg-app-surface p-2">
                      {filteredAutomations.length === 0 ? (
                        <p className="py-2 text-center text-xs text-app-muted">Nenhuma automacao encontrada</p>
                      ) : (
                        filteredAutomations.map((a) => (
                          <label
                            key={a.id}
                            className="flex cursor-pointer items-center gap-3 rounded-lg px-3 py-2 hover:bg-app-elevated/60 transition"
                          >
                            <input
                              type="checkbox"
                              checked={selectedAutomations.includes(a.id)}
                              onChange={() => toggleAutomation(a.id)}
                              className="accent-app-accent"
                            />
                            <div className="min-w-0 flex-1">
                              <span className="block truncate text-sm text-app-text">{a.name || a.code}</span>
                              {a.name && a.code && (
                                <span className="block truncate text-[11px] text-app-muted">{a.code}</span>
                              )}
                            </div>
                          </label>
                        ))
                      )}
                    </div>
                  )}
                </div>
                </>
              )}
            </>
          )}

          {error && (
            <p className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400">
              {error}
            </p>
          )}
        </div>

        <div className="flex gap-2 pt-4">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 rounded-xl border border-app-border px-4 py-2 text-sm text-app-muted hover:text-app-text"
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={loading}
            onClick={handleSave}
            className="flex-1 rounded-xl bg-app-accent px-4 py-2 text-sm font-semibold text-white hover:bg-app-accent/90 disabled:opacity-50"
          >
            {loading ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AdminUsersPage() {
  const { user: currentUser } = useAuth();
  const navigate = useNavigate();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [editUser, setEditUser] = useState(null);
  const [tempPassword, setTempPassword] = useState(null);
  const [actionLoading, setActionLoading] = useState(null);

  useEffect(() => {
    if (currentUser?.role !== 'admin') {
      navigate('/', { replace: true });
      return;
    }
    loadUsers();
  }, [currentUser, navigate]);

  async function loadUsers() {
    setLoading(true);
    setError('');
    try {
      const data = await adminListUsers();
      setUsers(data);
    } catch (err) {
      setError(err.message || 'Erro ao carregar usuarios');
    } finally {
      setLoading(false);
    }
  }

  function handleCreated(result) {
    setShowCreate(false);
    setTempPassword({ email: result.email, temporary_password: result.temporary_password });
    loadUsers();
  }

  async function handleResetPassword(userId) {
    if (!window.confirm('Gerar nova senha temporaria e encerrar todas as sessoes?')) return;
    setActionLoading(userId + '-reset');
    try {
      const result = await adminResetPassword(userId);
      const u = users.find((x) => x.id === userId);
      setTempPassword({ email: u?.email || '', temporary_password: result.temporary_password });
    } catch (err) {
      alert(err.message || 'Erro ao resetar senha');
    } finally {
      setActionLoading(null);
    }
  }

  async function handleRevokeSessions(userId) {
    if (!window.confirm('Encerrar todas as sessoes ativas deste usuario?')) return;
    setActionLoading(userId + '-revoke');
    try {
      await adminRevokeSessions(userId);
    } catch (err) {
      alert(err.message || 'Erro ao revogar sessoes');
    } finally {
      setActionLoading(null);
    }
  }

  if (currentUser?.role !== 'admin') return null;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-app-text">Usuarios</h1>
          <p className="text-xs text-app-muted mt-0.5">Gerenciamento de acesso ao painel</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={loadUsers}
            disabled={loading}
            className="inline-flex items-center gap-1.5 rounded-xl border border-app-border bg-app-surface/80 px-3 py-2 text-xs font-medium text-app-muted hover:text-app-text disabled:opacity-50"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Atualizar
          </button>
          <button
            type="button"
            onClick={() => setShowCreate(true)}
            className="inline-flex items-center gap-1.5 rounded-xl bg-app-accent px-4 py-2 text-xs font-semibold text-white hover:bg-app-accent/90"
          >
            <Plus className="h-3.5 w-3.5" />
            Novo usuario
          </button>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-12">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-app-accent border-t-transparent" />
        </div>
      ) : (
        <div className="rounded-2xl border border-app-border bg-app-elevated/60 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-app-border bg-app-surface/40">
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-app-muted">
                  Usuario
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-app-muted">
                  Perfil
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-app-muted">
                  Status
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-app-muted hidden md:table-cell">
                  Permissoes
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wide text-app-muted">
                  Acoes
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-app-border">
              {users.map((u) => (
                <tr key={u.id} className="hover:bg-app-surface/30 transition">
                  <td className="px-4 py-3">
                    <p className="font-medium text-app-text">{u.full_name}</p>
                    <p className="text-xs text-app-muted">{u.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                        u.role === 'admin'
                          ? 'bg-purple-500/15 text-purple-400'
                          : 'bg-blue-500/15 text-blue-400'
                      }`}
                    >
                      {u.role === 'admin' ? <ShieldCheck className="h-3 w-3" /> : null}
                      {u.role === 'admin' ? 'Admin' : 'Operador'}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${
                        u.is_active
                          ? 'bg-green-500/15 text-green-400'
                          : 'bg-red-500/15 text-red-400'
                      }`}
                    >
                      {u.is_active ? (
                        <UserCheck className="h-3 w-3" />
                      ) : (
                        <UserX className="h-3 w-3" />
                      )}
                      {u.is_active ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-4 py-3 hidden md:table-cell">
                    {u.role === 'admin' ? (
                      <span className="text-xs text-app-muted">Acesso total</span>
                    ) : u.permissions.length === 0 ? (
                      <span className="text-xs text-app-muted italic">Nenhuma</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {u.permissions.map((p) => (
                          <span
                            key={p}
                            className="rounded-md bg-app-surface px-1.5 py-0.5 text-[10px] text-app-muted"
                          >
                            {PERMISSIONS.find((x) => x.value === p)?.label ?? p}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center justify-end gap-1">
                      {u.id !== currentUser.id && (
                        <>
                          <button
                            type="button"
                            title="Editar acesso"
                            onClick={() => setEditUser(u)}
                            className="rounded-lg p-1.5 text-app-muted hover:bg-app-primary/10 hover:text-app-text transition"
                          >
                            <ShieldCheck className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            title="Resetar senha"
                            disabled={actionLoading === u.id + '-reset'}
                            onClick={() => handleResetPassword(u.id)}
                            className="rounded-lg p-1.5 text-app-muted hover:bg-amber-500/10 hover:text-amber-400 transition disabled:opacity-40"
                          >
                            <KeyRound className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            title="Encerrar sessoes"
                            disabled={actionLoading === u.id + '-revoke'}
                            onClick={() => handleRevokeSessions(u.id)}
                            className="rounded-lg p-1.5 text-app-muted hover:bg-red-500/10 hover:text-red-400 transition disabled:opacity-40"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {users.length === 0 && !loading && (
            <div className="py-10 text-center text-sm text-app-muted">Nenhum usuario encontrado</div>
          )}
        </div>
      )}

      {showCreate && <CreateUserModal onClose={() => setShowCreate(false)} onCreated={handleCreated} />}
      {editUser && (
        <EditAccessModal
          user={editUser}
          onClose={() => setEditUser(null)}
          onSaved={() => {
            setEditUser(null);
            loadUsers();
          }}
        />
      )}
      {tempPassword && <TempPasswordModal data={tempPassword} onClose={() => setTempPassword(null)} />}
    </div>
  );
}
