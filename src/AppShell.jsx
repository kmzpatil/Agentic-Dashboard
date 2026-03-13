import React, { useState } from 'react';
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
  const [activeTab, setActiveTab] = useState('Overview');
  const [isFilterOpen, setIsFilterOpen] = useState(true);
  const [isAiOpen, setIsAiOpen] = useState(false);

  const overview = useApi(`${API_BASE}/overview`, []);

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
      <div className="flex items-center px-6 py-4 bg-[#050505] border-b border-neutral-900">
        <h1 className="text-red-500 font-black text-2xl tracking-tighter">FRAMMER AI</h1>
        <div className="ml-4 text-xs font-bold tracking-widest text-neutral-600 uppercase mt-1">Nerve Center</div>
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
          {activeTab === 'Explorer' && <ExplorerModule />}
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
