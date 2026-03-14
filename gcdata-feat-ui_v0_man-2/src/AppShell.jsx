import React, { useEffect, useState } from 'react';
import {
  BarChart3,
  LayoutDashboard,
  Funnel,
  Microscope,
  Stethoscope,
  MessageSquare,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import './lib/chartSetup';
import { customStyles, API_BASE } from './lib/constants';
import { useApi } from './hooks/useApi';
import PipelineRail from './components/layout/PipelineRail';
import FilterDock from './components/layout/FilterDock';
import OverviewModule from './features/overview/OverviewModule';
import UsageTrendsModule from './features/usage/UsageTrendsModule';
import FunnelModule from './features/funnel/FunnelModule';
import ExplorerModule from './features/explorer/ExplorerModule';
import ComingSoonModule from './features/shared/ComingSoonModule';

export default function AppShell() {
  const [authToken, setAuthToken] = useState(() => localStorage.getItem('frammer_auth_token') || '');
  const [authUser, setAuthUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem('frammer_auth_user') || 'null');
    } catch (_error) {
      return null;
    }
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
      if (!authToken) {
        setAuthLoading(false);
        setAuthUser(null);
        return;
      }

      try {
        const response = await fetch(`${API_BASE}/auth/me`, {
          headers: {
            Authorization: `Bearer ${authToken}`,
          },
        });

        if (!response.ok) {
          throw new Error('Session expired');
        }

        const payload = await response.json();
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

  const overview = useApi(authUser ? `${API_BASE}/overview` : null, [authUser?.id]);

  const handleLogin = async (event) => {
    event.preventDefault();
    setLoginError('');
    setLoginSubmitting(true);
    try {
      const response = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username: loginUsername, password: loginPassword }),
      });

      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.error || 'Login failed');
      }

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
      <div className="h-screen w-full bg-[#050505] text-white flex items-center justify-center">
        <div className="text-neutral-400 text-sm tracking-wide">Restoring session...</div>
      </div>
    );
  }

  if (!authToken || !authUser) {
    return (
      <div className="h-screen w-full bg-[#050505] text-white flex items-center justify-center px-4">
        <div className="w-full max-w-md bg-[#111111] border border-neutral-800 rounded-xl p-6 space-y-4">
          <div>
            <h1 className="text-red-500 font-black text-2xl tracking-tighter">FRAMMER AI</h1>
            <p className="text-neutral-400 text-sm mt-2">Sign in with your local username and password.</p>
          </div>
          <form className="space-y-3" onSubmit={handleLogin}>
            <div>
              <label className="block text-xs text-neutral-500 mb-2">USERNAME</label>
              <input
                type="text"
                value={loginUsername}
                onChange={(event) => setLoginUsername(event.target.value)}
                className="w-full bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white"
                placeholder="website_admin"
                required
              />
            </div>
            <div>
              <label className="block text-xs text-neutral-500 mb-2">PASSWORD</label>
              <input
                type="password"
                value={loginPassword}
                onChange={(event) => setLoginPassword(event.target.value)}
                className="w-full bg-[#0A0A0A] border border-neutral-700 rounded px-3 py-2 text-white"
                placeholder="********"
                required
              />
            </div>
            {loginError && <div className="text-red-400 text-sm">{loginError}</div>}
            <button
              type="submit"
              disabled={loginSubmitting}
              className="w-full px-4 py-2 rounded bg-white text-black font-bold hover:bg-neutral-200 transition-colors disabled:opacity-50"
            >
              {loginSubmitting ? 'Signing in...' : 'Sign In'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  const navItems = [
    { id: 'Overview', icon: <LayoutDashboard size={16} /> },
    { id: 'Usage & Trends', icon: <BarChart3 size={16} /> },
    { id: 'Funnel', icon: <Funnel size={16} /> },
    { id: 'Explorer', icon: <Microscope size={16} /> },
    { id: 'Data Health', icon: <Stethoscope size={16} />, disabled: true },
  ];

  return (
    <div className="h-screen w-full bg-[#0A0A0A] flex flex-col font-sans overflow-hidden text-white">
      <style>{customStyles}</style>
      <div className="flex items-center justify-between px-6 py-4 bg-[#050505] border-b border-neutral-900 gap-4">
        <div className="flex items-center">
          <h1 className="text-red-500 font-black text-2xl tracking-tighter">FRAMMER AI</h1>
          <div className="ml-4 text-xs font-bold tracking-widest text-neutral-600 uppercase mt-1">Nerve Center</div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-xs text-neutral-400">
            {authUser.username} • {authUser.role.replace('_', ' ')}
            {authUser.clientName ? ` • ${authUser.clientName}` : ''}
            {authUser.userId ? ` • User ${authUser.userId}` : ''}
          </div>
          <button onClick={handleLogout} className="px-3 py-1.5 text-xs rounded bg-neutral-800 text-neutral-200 hover:bg-neutral-700 transition-colors">
            Logout
          </button>
        </div>
      </div>

      <PipelineRail overview={overview.data} />

      <div className="bg-[#0A0A0A] border-b border-neutral-900 px-4 py-3 flex items-center justify-between z-10">
        <div className="flex space-x-2 overflow-auto hide-scrollbar">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => !item.disabled && setActiveTab(item.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-full text-sm font-bold transition-colors ${
                activeTab === item.id ? 'bg-[#1A1A1A] text-white' : item.disabled ? 'text-neutral-700 cursor-not-allowed' : 'text-neutral-500 hover:bg-[#111111] hover:text-neutral-300'
              }`}
            >
              {item.icon} {item.id}
            </button>
          ))}
        </div>
        <button onClick={() => setIsAiOpen(true)} className="flex items-center gap-2 px-6 py-2 bg-white text-black rounded-full text-sm font-bold hover:bg-neutral-200 transition-colors">
          <MessageSquare size={16} /> Ask Frammer AI
        </button>
      </div>

      <div className="flex flex-1 overflow-hidden relative">
        <FilterDock isOpen={isFilterOpen} setIsOpen={setIsFilterOpen} />

        <main className="flex-1 bg-[#050505] relative overflow-hidden">
          {activeTab === 'Overview' && <OverviewModule />}
          {activeTab === 'Usage & Trends' && <UsageTrendsModule />}
          {activeTab === 'Funnel' && <FunnelModule />}
          {activeTab === 'Explorer' && <ExplorerModule authUser={authUser} />}
          {activeTab === 'Data Health' && <ComingSoonModule title="Data Health" />}
        </main>

        {!isAiOpen && (
          <button onClick={() => setIsAiOpen(true)} className="absolute bottom-16 right-6 w-14 h-14 bg-white text-black rounded-full shadow-lg flex items-center justify-center hover:bg-neutral-200 hover:scale-105 transition-all z-20">
            <Sparkles size={24} />
          </button>
        )}

        <div className={`absolute top-0 right-0 h-full w-[400px] bg-[#0A0A0A] shadow-2xl border-l border-neutral-900 transform transition-transform duration-300 ease-in-out z-30 flex flex-col ${isAiOpen ? 'translate-x-0' : 'translate-x-full'}`}>
          <div className="p-5 border-b border-neutral-900 flex items-center justify-between bg-[#050505] text-white">
            <div className="flex items-center gap-2 font-black tracking-tight text-red-400"><MessageSquare size={18} /> FRAMMER AI COPILOT</div>
            <button onClick={() => setIsAiOpen(false)} className="text-neutral-500 hover:text-white transition-colors"><ChevronRight size={20} /></button>
          </div>
          <div className="flex-1 p-5 overflow-y-auto space-y-4 bg-[#0A0A0A] text-sm text-neutral-400">
            <p>AI copilot is intentionally out-of-scope in this phase.</p>
            <p>Use Usage & Trends, Funnel, and Explorer for analysis and drilldowns.</p>
          </div>
        </div>
      </div>
    </div>
  );
}
