import React, { useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  Bot,
  Funnel,
  Route,
  LayoutDashboard,
  Microscope,
  FlaskConical,
  Braces,
} from 'lucide-react';
import './lib/chartSetup';
import { API_BASE, customStyles } from './lib/constants';
import { useApi } from './hooks/useApi';
import OverviewModule from './features/overview/OverviewModule';
import UsageTrendsModule from './features/usage/UsageTrendsModule';
import FunnelModule from './features/funnel/FunnelModule';
import UserJourneyModule from './features/journey/UserJourneyModule';
import ExplorerModule from './features/explorer/ExplorerModule';
import TalkToDataModule from './features/talk/TalkToDataModule';
import LabsModule from './features/labs/LabsModule';

function readRouteState() {
  const params = new URLSearchParams(window.location.search);
  return Object.fromEntries(params.entries());
}


export default function AppShell() {
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('frammer_auth_token') || '');
  const [authUser, setAuthUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('frammer_auth_user') || 'null'); }
    catch (_error) { return null; }
  });
  const [authLoading, setAuthLoading] = useState(Boolean(localStorage.getItem('frammer_auth_token')));
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginSubmitting, setLoginSubmitting] = useState(false);
  const [routeState, setRouteState] = useState(readRouteState);

  useEffect(() => {
    const onPopState = () => setRouteState(readRouteState());
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  const navigate = (nextState) => {
    const params = new URLSearchParams(window.location.search);
    Object.entries(nextState || {}).forEach(([key, value]) => {
      if (value === undefined || value === null || value === '') params.delete(key);
      else params.set(key, String(value));
    });
    if (!params.get('view')) params.set('view', 'mission-control');
    const query = params.toString();
    const nextUrl = `${window.location.pathname}${query ? `?${query}` : ''}`;
    window.history.replaceState({}, '', nextUrl);
    setRouteState(Object.fromEntries(params.entries()));
  };

  useEffect(() => {
    if (!routeState.view) {
      navigate({ view: 'mission-control' });
    }
  }, [routeState.view]);

  useEffect(() => {
    const bootstrapSession = async () => {
      if (!authToken) {
        setAuthLoading(false);
        setAuthUser(null);
        return;
      }

      try {
        const res = await fetch(`${API_BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${authToken}` },
        });
        if (!res.ok) throw new Error('Session expired');
        const payload = await res.json();
        setAuthUser(payload.user || null);
        localStorage.setItem('frammer_auth_user', JSON.stringify(payload.user || null));
      } catch (_error) {
        localStorage.removeItem('frammer_auth_token');
        localStorage.removeItem('frammer_auth_user');
        setAuthToken('');
        setAuthUser(null);
      } finally {
        setAuthLoading(false);
      }
    };
    bootstrapSession();
  }, [authToken]);

  const health = useApi(authUser ? `${API_BASE}/health` : null, [authUser?.id]);
  const activeView = routeState.view || 'mission-control';

  const navItems = useMemo(() => ([
    { id: 'mission-control', label: 'Mission Control', icon: <LayoutDashboard size={16} /> },
    { id: 'trends', label: 'Trends', icon: <BarChart3 size={16} /> },
    { id: 'funnel', label: 'Funnel', icon: <Funnel size={16} /> },
    { id: 'journey', label: 'Metrics', icon: <Route size={16} /> },
    { id: 'explorer', label: 'Explorer', icon: <Microscope size={16} /> },
    { id: 'copilot', label: 'Copilot', icon: <Bot size={16} /> },
    { id: 'labs', label: 'Labs', icon: <FlaskConical size={16} /> },
  ]), []);

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoginError('');
    setLoginSubmitting(true);

    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginUsername, password: loginPassword }),
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(payload.detail || payload.error || 'Login failed');
      localStorage.setItem('frammer_auth_token', payload.token);
      localStorage.setItem('frammer_auth_user', JSON.stringify(payload.user));
      setAuthToken(payload.token);
      setAuthUser(payload.user);
      setLoginPassword('');
    } catch (error) {
      setLoginError(error.message || 'Login failed');
    } finally {
      setLoginSubmitting(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('frammer_auth_token');
    localStorage.removeItem('frammer_auth_user');
    setAuthToken('');
    setAuthUser(null);
    setLoginUsername('');
    setLoginPassword('');
  };

  if (authLoading) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[#050505] text-white">
        <div className="text-sm tracking-wide text-neutral-400">Restoring session...</div>
      </div>
    );
  }

  if (!authToken || !authUser) {
    return (
      <div className="flex h-screen w-full items-center justify-center bg-[#050505] px-4 text-white">
        <div className="w-full max-w-md rounded-3xl border border-neutral-800 bg-[#101010] p-8 shadow-[0_30px_120px_rgba(0,0,0,0.55)]">
          <div className="mb-6">
            <div className="text-[11px] font-bold uppercase tracking-[0.25em] text-neutral-500">Frammer Analytics OS</div>
            <h1 className="mt-2 text-3xl font-black tracking-tight text-red-500">FRAMMER AI</h1>
            <p className="mt-2 text-sm text-neutral-500">Sign in to open Mission Control.</p>
          </div>
          <form className="space-y-4" onSubmit={handleLogin}>
            <div>
              <label className="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-neutral-500">Username</label>
              <input
                type="text"
                value={loginUsername}
                onChange={(event) => setLoginUsername(event.target.value)}
                className="w-full rounded-2xl border border-neutral-700 bg-[#0A0A0A] px-4 py-3 text-white placeholder-neutral-600 focus:border-red-500 focus:outline-none"
                placeholder="website_admin"
                required
              />
            </div>
            <div>
              <label className="mb-2 block text-xs font-bold uppercase tracking-[0.18em] text-neutral-500">Password</label>
              <input
                type="password"
                value={loginPassword}
                onChange={(event) => setLoginPassword(event.target.value)}
                className="w-full rounded-2xl border border-neutral-700 bg-[#0A0A0A] px-4 py-3 text-white placeholder-neutral-600 focus:border-red-500 focus:outline-none"
                placeholder="••••••••"
                required
              />
            </div>
            {loginError && <div className="text-sm text-red-400">{loginError}</div>}
            <button
              type="submit"
              disabled={loginSubmitting}
              className="w-full rounded-2xl bg-white px-4 py-3 text-sm font-bold text-black transition-colors hover:bg-neutral-200 disabled:opacity-50"
            >
              {loginSubmitting ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen w-full flex-col overflow-hidden bg-[#050505] text-white">
      <style>{customStyles}</style>

      <header className="border-b border-neutral-900 bg-[#050505] px-6 py-4">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="min-w-0">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-black tracking-tight text-red-500">FRAMMER AI</h1>
              <div className="inline-flex items-center gap-2 rounded-full border border-neutral-800 bg-[#111111] px-3 py-1 text-[11px] font-bold uppercase tracking-[0.2em] text-neutral-500">
                <Braces size={12} />
                Analytics OS
              </div>
            </div>
            <p className="mt-2 text-sm text-neutral-500">A single workspace for performance monitoring, operating priorities, and AI-guided analysis.</p>
          </div>

          <div className="flex items-center gap-3">
            {/* DB status — single dot indicator */}
            {health.data?.services?.database && (() => {
              const dbOk = Boolean(health.data.services.database.ok);
              return (
                <div className="flex items-center gap-2 rounded-full border border-neutral-800 bg-[#111111] px-3 py-1.5">
                  <div className={`h-2 w-2 rounded-full ${dbOk ? 'bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.6)]' : 'bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]'}`} />
                  <span className="text-xs font-semibold text-neutral-400">DB</span>
                </div>
              );
            })()}

            <div className="h-4 w-px bg-neutral-800" />

            <span className="text-sm text-neutral-400">{authUser.username}</span>
            <button
              onClick={handleLogout}
              className="rounded-full bg-neutral-800 px-3 py-1.5 text-xs text-neutral-300 transition-colors hover:bg-neutral-700"
            >
              Logout
            </button>
          </div>
        </div>
      </header>

      <nav className="border-b border-neutral-900 bg-[#090909] px-4 py-3">
        <div className="flex gap-2 overflow-auto hide-scrollbar">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => navigate({ view: item.id })}
              className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-bold transition-colors ${
                activeView === item.id
                  ? 'bg-[#171717] text-white'
                  : 'text-neutral-500 hover:bg-[#111111] hover:text-neutral-200'
              }`}
            >
              {item.icon}
              {item.label}
            </button>
          ))}
        </div>
      </nav>

      <main className="flex-1 overflow-hidden">
        {activeView === 'mission-control' && <OverviewModule routeState={routeState} onNavigate={navigate} />}
        {activeView === 'trends' && <UsageTrendsModule authUser={authUser} routeState={routeState} onNavigate={navigate} />}
        {activeView === 'funnel' && <FunnelModule authUser={authUser} routeState={routeState} onNavigate={navigate} />}
        {activeView === 'journey' && <UserJourneyModule authUser={authUser} routeState={routeState} onNavigate={navigate} />}
        {activeView === 'explorer' && <ExplorerModule authUser={authUser} routeState={routeState} onNavigate={navigate} />}
        {activeView === 'copilot' && <TalkToDataModule authToken={authToken} routeState={routeState} onNavigate={navigate} />}
        {activeView === 'labs' && <LabsModule />}
      </main>
    </div>
  );
}
