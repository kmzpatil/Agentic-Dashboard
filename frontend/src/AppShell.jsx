import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  LayoutDashboard,
  Funnel,
  Microscope,
  MessageSquare,
  Sparkles,
  Database,
} from 'lucide-react';
import './lib/chartSetup';
import { customStyles, API_BASE } from './lib/constants';
import { useApi } from './hooks/useApi';
import PipelineRail from './components/layout/PipelineRail';
import FilterDock from './components/layout/FilterDock';
import ChatPanel from './components/chat/ChatPanel';
import OverviewModule from './features/overview/OverviewModule';
import UsageTrendsModule from './features/usage/UsageTrendsModule';
import FunnelModule from './features/funnel/FunnelModule';
import ExplorerModule from './features/explorer/ExplorerModule';
import TalkToDataModule from './features/talk/TalkToDataModule';

function StatusPill({ label, ok, detail }) {
  const tone = ok
    ? 'border-emerald-500/30 text-emerald-300 bg-emerald-500/10'
    : 'border-amber-500/30 text-amber-300 bg-amber-500/10';
  return (
    <div className={`rounded-full border px-3 py-1 text-[11px] font-bold uppercase tracking-[0.2em] ${tone}`}>
      {label}: {ok ? 'online' : 'degraded'}
      {detail ? <span className="ml-2 normal-case tracking-normal text-[10px] opacity-80">{detail}</span> : null}
    </div>
  );
}

export default function AppShell() {
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('frammer_auth_token') || '');
  const [authUser, setAuthUser] = useState(() => {
    try { return JSON.parse(localStorage.getItem('frammer_auth_user') || 'null'); }
    catch (_e) { return null; }
  });
  const [authLoading, setAuthLoading] = useState(Boolean(localStorage.getItem('frammer_auth_token')));
  const [loginUsername, setLoginUsername] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [loginError, setLoginError] = useState('');
  const [loginSubmitting, setLoginSubmitting] = useState(false);

  const [activeTab, setActiveTab] = useState('Overview');
  const [isFilterOpen, setIsFilterOpen] = useState(true);
  const [isAiOpen, setIsAiOpen] = useState(false);

  useEffect(() => {
    const bootstrapSession = async () => {
      if (!authToken) { setAuthLoading(false); setAuthUser(null); return; }
      try {
        const res = await fetch(`${API_BASE}/auth/me`, {
          headers: { Authorization: `Bearer ${authToken}` },
        });
        if (!res.ok) throw new Error('Session expired');
        const payload = await res.json();
        setAuthUser(payload.user || null);
        localStorage.setItem('frammer_auth_user', JSON.stringify(payload.user || null));
      } catch (_e) {
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

  const overview = useApi(authUser ? `${API_BASE}/overview` : null, [authUser?.id]);
  const health = useApi(authUser ? `${API_BASE}/health` : null, [authUser?.id]);

  const databaseOk = health.data?.services?.database?.ok;
  const agentOk = health.data?.services?.agent?.ok;
  const missingTables = health.data?.services?.database?.missingTables || [];
  const agentDetail = health.data?.services?.agent?.error || '';

  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError('');
    setLoginSubmitting(true);
    try {
      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username: loginUsername, password: loginPassword }),
      });
      const payload = await res.json();
      if (!res.ok) throw new Error(payload.error || 'Login failed');
      localStorage.setItem('frammer_auth_token', payload.token);
      localStorage.setItem('frammer_auth_user', JSON.stringify(payload.user));
      setAuthToken(payload.token);
      setAuthUser(payload.user);
      setLoginPassword('');
    } catch (err) {
      setLoginError(err.message || 'Login failed');
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
      <div className="h-screen w-full bg-[#050505] text-white flex items-center justify-center">
        <div className="text-neutral-400 text-sm tracking-wide">Restoring session...</div>
      </div>
    );
  }

  if (!authToken || !authUser) {
    return (
      <div className="h-screen w-full bg-[#050505] text-white flex items-center justify-center px-4">
        <div className="w-full max-w-md bg-[#111111] border border-neutral-800 rounded-xl p-8 space-y-6">
          <div>
            <h1 className="text-red-500 font-black text-2xl tracking-tighter">FRAMMER AI</h1>
            <p className="text-neutral-500 text-sm mt-1">Nerve Centre — sign in to continue</p>
          </div>
          <form className="space-y-4" onSubmit={handleLogin}>
            <div>
              <label className="block text-xs font-bold text-neutral-500 mb-2 tracking-widest uppercase">Username</label>
              <input
                type="text"
                value={loginUsername}
                onChange={(e) => setLoginUsername(e.target.value)}
                className="w-full bg-[#0A0A0A] border border-neutral-700 rounded-lg px-4 py-2.5 text-white placeholder-neutral-600 focus:outline-none focus:border-red-500 transition-colors"
                placeholder="website_admin"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-neutral-500 mb-2 tracking-widest uppercase">Password</label>
              <input
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                className="w-full bg-[#0A0A0A] border border-neutral-700 rounded-lg px-4 py-2.5 text-white placeholder-neutral-600 focus:outline-none focus:border-red-500 transition-colors"
                placeholder="••••••••"
                required
              />
            </div>
            {loginError && <div className="text-red-400 text-sm">{loginError}</div>}
            <button
              type="submit"
              disabled={loginSubmitting}
              className="w-full px-4 py-3 rounded-lg bg-white text-black font-bold hover:bg-neutral-200 transition-colors disabled:opacity-50"
            >
              {loginSubmitting ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
          <p className="text-xs text-neutral-600 text-center">
            Run <code className="text-neutral-400">npm run seed:auth</code> to create default users.
          </p>
        </div>
      </div>
    );
  }

  const isTalkTab = activeTab === 'Talk to Your Data';

  const navItems = [
    { id: 'Overview',         icon: <LayoutDashboard size={16} /> },
    { id: 'Usage & Trends',   icon: <BarChart3 size={16} /> },
    { id: 'Funnel',           icon: <Funnel size={16} /> },
    { id: 'Explorer',         icon: <Microscope size={16} /> },
    { id: 'Talk to Your Data', icon: <Database size={16} /> },
  ];

  return (
    <div className="h-screen w-full bg-[#0A0A0A] flex flex-col font-sans overflow-hidden text-white">
      <style>{customStyles}</style>

      {/* Top header */}
      <div className="flex items-center justify-between gap-4 px-6 py-4 bg-[#050505] border-b border-neutral-900">
        <div className="flex items-center min-w-0">
          <h1 className="text-red-500 font-black text-2xl tracking-tighter">FRAMMER AI</h1>
          <div className="ml-4 text-xs font-bold tracking-widest text-neutral-600 uppercase mt-1">Nerve Center</div>
        </div>
        <div className="flex flex-wrap items-center justify-end gap-2">
          {health.data && (
            <>
              <StatusPill
                label="DB"
                ok={Boolean(databaseOk)}
                detail={missingTables.length
                  ? `${missingTables.length} missing table${missingTables.length === 1 ? '' : 's'}`
                  : health.data?.services?.database?.database}
              />
              <StatusPill
                label="Agent"
                ok={Boolean(agentOk)}
                detail={agentOk ? 'Ready for chat' : (agentDetail || 'Start the agent service')}
              />
            </>
          )}
          <div className="text-xs text-neutral-500 ml-2">
            {authUser.username} · <span className="text-neutral-400">{authUser.role.replace(/_/g, ' ')}</span>
            {authUser.clientName ? ` · ${authUser.clientName}` : ''}
          </div>
          <button
            onClick={handleLogout}
            className="px-3 py-1.5 text-xs rounded-full bg-neutral-800 text-neutral-300 hover:bg-neutral-700 transition-colors"
          >
            Logout
          </button>
        </div>
      </div>

      {!isTalkTab && <PipelineRail overview={overview.data} />}

      {/* Navigation bar */}
      <div className="bg-[#0A0A0A] border-b border-neutral-900 px-4 py-3 flex items-center justify-between z-10">
        <div className="flex space-x-2 overflow-auto hide-scrollbar">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => !item.disabled && setActiveTab(item.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold transition-colors ${
                activeTab === item.id
                  ? 'bg-[#1A1A1A] text-white'
                  : item.disabled
                    ? 'text-neutral-700 cursor-not-allowed'
                    : 'text-neutral-500 hover:bg-[#111111] hover:text-neutral-300'
              }`}
            >
              {item.icon} {item.id}
            </button>
          ))}
        </div>
        {!isTalkTab && (
          <button
            onClick={() => setIsAiOpen(true)}
            className="flex items-center gap-2 px-6 py-2 bg-white text-black rounded-full text-sm font-bold hover:bg-neutral-200 transition-colors"
          >
            <span className={`w-2 h-2 rounded-full ${agentOk === false ? 'bg-amber-500' : 'bg-emerald-500'}`} />
            <MessageSquare size={16} /> Ask Frammer AI
          </button>
        )}
      </div>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden relative">
        {!isTalkTab && <FilterDock isOpen={isFilterOpen} setIsOpen={setIsFilterOpen} />}

        <main className="flex-1 bg-[#050505] relative overflow-hidden">
          {activeTab === 'Overview'         && <OverviewModule />}
          {activeTab === 'Usage & Trends'   && <UsageTrendsModule />}
          {activeTab === 'Funnel'           && <FunnelModule />}
          {activeTab === 'Explorer'         && <ExplorerModule authUser={authUser} />}
          {activeTab === 'Talk to Your Data' && <TalkToDataModule authToken={authToken} />}
        </main>

        {/* Floating AI button (hidden on Talk to Data tab) */}
        {!isAiOpen && !isTalkTab && (
          <button
            onClick={() => setIsAiOpen(true)}
            className="absolute bottom-16 right-6 w-14 h-14 bg-white text-black rounded-full shadow-lg flex items-center justify-center hover:bg-neutral-200 hover:scale-105 transition-all z-20"
          >
            <Sparkles size={24} />
          </button>
        )}

        {/* AI chat panel (slide-in) */}
        {!isTalkTab && (
          <ChatPanel
            isOpen={isAiOpen}
            onClose={() => setIsAiOpen(false)}
            authToken={authToken}
            agentOk={agentOk}
            databaseOk={databaseOk}
          />
        )}
      </div>
    </div>
  );
}
