import React from 'react';
import { FlaskConical, Sparkles } from 'lucide-react';
import SimulatorModule from '../simulator/SimulatorModule';

export default function LabsModule() {
  return (
    <div className="h-full overflow-y-auto bg-[#050505] px-6 py-6 space-y-6">
      <section className="rounded-[28px] border border-neutral-800 bg-[radial-gradient(circle_at_top_left,_rgba(239,68,68,0.18),_transparent_50%),linear-gradient(180deg,#141414,_#090909)] p-6">
        <div className="flex items-start gap-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-white/5 text-red-400">
            <FlaskConical size={22} />
          </div>
          <div>
            <div className="text-[11px] font-bold uppercase tracking-[0.22em] text-neutral-500">Frammer Labs</div>
            <h2 className="mt-2 text-2xl font-black tracking-tight text-white">Experimental forecasting and simulation live here.</h2>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-neutral-400">
              Use Labs for scenario testing and experimental analysis without mixing those flows into the core
              operating views used for day-to-day decisions.
            </p>
            <div className="mt-4 inline-flex items-center gap-2 rounded-full border border-neutral-700 bg-[#111111] px-3 py-1.5 text-[11px] uppercase tracking-[0.18em] text-neutral-400">
              <Sparkles size={12} />
              Experimental Surface
            </div>
          </div>
        </div>
      </section>

      <SimulatorModule />
    </div>
  );
}
