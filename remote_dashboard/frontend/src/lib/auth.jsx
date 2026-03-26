import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { setAuthToken, registerOnUnauthorized } from './api';

const AuthContext = createContext(null);

async function _doRefresh() {
  try {
    const resp = await fetch('/dashboard-api/auth/refresh', {
      method: 'POST',
      credentials: 'same-origin',
    });
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}

async function _fetchMe(token) {
  try {
    const resp = await fetch('/dashboard-api/auth/me', {
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'same-origin',
    });
    if (!resp.ok) return null;
    return await resp.json();
  } catch {
    return null;
  }
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    setToken(null);
    setUser(null);
    setAuthToken(null);
  }, []);

  // Register callback so api.js can clear session on 401 after failed refresh
  useEffect(() => {
    registerOnUnauthorized(clearSession);
    return () => registerOnUnauthorized(null);
  }, [clearSession]);

  // Restore session on mount via refresh cookie
  useEffect(() => {
    (async () => {
      const tokenData = await _doRefresh();
      if (tokenData?.access_token) {
        setAuthToken(tokenData.access_token);
        const userData = await _fetchMe(tokenData.access_token);
        if (userData) {
          setToken(tokenData.access_token);
          setUser(userData);
        } else {
          setAuthToken(null);
        }
      }
      setLoading(false);
    })();
  }, []);

  // Proactive token refresh: 2 min before expiry (access token = 30 min)
  useEffect(() => {
    if (!token) return;
    const timer = setTimeout(async () => {
      const tokenData = await _doRefresh();
      if (tokenData?.access_token) {
        setAuthToken(tokenData.access_token);
        setToken(tokenData.access_token);
      } else {
        clearSession();
      }
    }, (30 * 60 - 120) * 1000);
    return () => clearTimeout(timer);
  }, [token, clearSession]);

  const login = useCallback(async (email, password) => {
    const resp = await fetch('/dashboard-api/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
      credentials: 'same-origin',
      body: JSON.stringify({ email, password }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || 'Login falhou');
    setAuthToken(data.access_token);
    const userData = await _fetchMe(data.access_token);
    setToken(data.access_token);
    setUser(userData);
  }, []);

  const logout = useCallback(async () => {
    try {
      await fetch('/dashboard-api/auth/logout', {
        method: 'POST',
        credentials: 'same-origin',
      });
    } catch {
      // ignore
    }
    clearSession();
  }, [clearSession]);

  return (
    <AuthContext.Provider value={{ user, token, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth deve ser usado dentro de AuthProvider');
  return ctx;
}
