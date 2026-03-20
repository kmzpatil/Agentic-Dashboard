import React, { useEffect, useRef, useState } from 'react';
import { ShieldCheck } from 'lucide-react';
import useDqaData from './hooks/useDqaData';
import OverviewTab from './components/OverviewTab';
import DashboardTab from './components/DashboardTab';
import EventLoggerTab from './components/EventLoggerTab';
import SchemasConfigTab from './components/SchemasConfigTab';

const DQA_TABS = [
  { id: 'overview', label: 'Overview' },
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'logger', label: 'Event Logger' },
  { id: 'schemas', label: 'Schemas & Config' },
];

export default function LabsModule({ authUser, routeState = {}, onNavigate }) {
  const [activeTab, setActiveTab] = useState('overview');
  const autoStarted = useRef(false);
  const dqa = useDqaData();

  // Auto-start simulation on mount
  useEffect(() => {
    if (autoStarted.current) return;
    if (dqa.status && !dqa.status.running) {
      autoStarted.current = true;
      dqa.runAction('start', { ops_per_batch: '5', interval: '2' });
    } else if (!dqa.status && !dqa.loading) {
      autoStarted.current = true;
      dqa.runAction('start', { ops_per_batch: '5', interval: '2' });
    }
  }, [dqa.status, dqa.loading]);

  return (
    <div className="h-full overflow-y-auto bg-[#050505]">
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden>
        <div className="absolute -top-32 left-1/2 -translate-x-1/2 w-[700px] h-[340px] rounded-full bg-sky-600/5 blur-[120px]" />
      </div>

      <div className="relative mx-auto w-full max-w-[1440px] px-6 pt-6 pb-12 space-y-6">
        {/* Header */}
        <div className="flex items-center gap-4">
          <div className="flex items-center justify-center w-10 h-10 rounded-2xl bg-sky-500/10 border border-sky-500/20">
            <ShieldCheck size={20} className="text-sky-400" />
          </div>
          <div>
            <h2 className="text-2xl font-black tracking-tight">Data Quality Analyser</h2>
            <p className="text-sm text-neutral-500 mt-0.5">
              Pipeline simulation with real-time quality scoring and error injection.
              {dqa.status?.running && (
                <span className="ml-2 inline-flex items-center gap-1.5 text-emerald-400">
                  <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  Live
                </span>
              )}
            </p>
          </div>
        </div>

        {dqa.error && (
          <div className="rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
            {dqa.error}
          </div>
        )}

        {/* Tabs */}
        <div className="flex items-center gap-3">
          <span className="text-[9.5px] font-bold uppercase tracking-[0.2em] text-neutral-600">Views</span>
          <div className="flex gap-1">
            {DQA_TABS.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={[
                  'relative px-3.5 py-1.5 rounded-full text-[11.5px] font-semibold transition-all duration-150',
                  activeTab === tab.id
                    ? 'text-white'
                    : 'text-neutral-600 hover:text-neutral-300',
                ].join(' ')}
              >
                {activeTab === tab.id && (
                  <span className="absolute inset-0 rounded-full bg-white/8 ring-1 ring-white/10" />
                )}
                <span className="relative">{tab.label}</span>
              </button>
            ))}
          </div>
          <div className="flex-1 h-px bg-neutral-900" />
        </div>

        {/* Tab content */}
        {activeTab === 'overview' && <OverviewTab dqa={dqa} />}
        {activeTab === 'dashboard' && <DashboardTab dqa={dqa} />}
        {activeTab === 'logger' && <EventLoggerTab dqa={dqa} />}
        {activeTab === 'schemas' && <SchemasConfigTab dqa={dqa} />}
      </div>
    </div>
  );
}
