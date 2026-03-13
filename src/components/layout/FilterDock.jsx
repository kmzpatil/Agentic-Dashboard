import React from 'react';
import {
  ChevronLeft,
  Menu,
  Filter,
  Calendar,
  Building,
  Tv,
  User,
  Globe,
  Download,
  Upload,
  Sparkles,
  RefreshCcw,
} from 'lucide-react';

function FilterSelect({ icon, label, defaultValue = 'All' }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="flex items-center gap-2 text-neutral-400">{icon} {label}</span>
      <select className="border-none bg-transparent text-white font-medium text-right outline-none cursor-pointer">
        <option>{defaultValue}</option>
      </select>
    </div>
  );
}

export default function FilterDock({ isOpen, setIsOpen }) {
  return (
    <div className={`bg-[#0A0A0A] border-r border-neutral-900 transition-all duration-300 flex flex-col h-full ${isOpen ? 'w-72' : 'w-16'}`}>
      <div className="p-4 border-b border-neutral-900 flex items-center justify-between">
        {isOpen && <span className="font-bold text-white flex items-center gap-2 tracking-tight"><Filter size={18} /> FILTERS</span>}
        <button onClick={() => setIsOpen(!isOpen)} className="p-1 hover:bg-[#1A1A1A] rounded text-neutral-400">
          {isOpen ? <ChevronLeft size={20} /> : <Menu size={20} />}
        </button>
      </div>

      <div className={`p-4 flex-1 overflow-y-auto space-y-6 ${!isOpen && 'hidden'}`}>
        <div className="space-y-3">
          <label className="text-xs font-bold tracking-wider text-neutral-500 flex items-center gap-2"><Calendar size={14} /> DATE RANGE</label>
          <select className="w-full text-sm border border-neutral-800 rounded-md p-2 bg-[#111111] text-white outline-none">
            <option>Mar 2025 - Mar 2026</option>
          </select>
        </div>

        <div className="border-t border-neutral-900 pt-4 space-y-3">
          <FilterSelect icon={<Building size={14} />} label="Company" />
          <FilterSelect icon={<Tv size={14} />} label="Channel" />
          <FilterSelect icon={<User size={14} />} label="User" />
          <FilterSelect icon={<Globe size={14} />} label="Language" />
          <FilterSelect icon={<Upload size={14} />} label="Input Type" />
          <FilterSelect icon={<Download size={14} />} label="Output Type" />
        </div>

        <div className="pt-4 flex gap-2">
          <button className="flex-1 bg-white text-black text-sm font-bold py-2 rounded-full hover:bg-neutral-200 flex items-center justify-center gap-2 transition-colors">
            <Sparkles size={14} /> Apply AI
          </button>
          <button className="flex-1 bg-[#1A1A1A] text-neutral-300 text-sm font-bold py-2 rounded-full hover:bg-[#2A2A2A] flex items-center justify-center gap-2 transition-colors">
            <RefreshCcw size={14} /> Reset
          </button>
        </div>
      </div>
    </div>
  );
}
