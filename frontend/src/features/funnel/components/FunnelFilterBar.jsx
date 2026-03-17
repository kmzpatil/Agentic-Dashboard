import React from 'react';
import { X } from 'lucide-react';
import { useApi } from '../../../hooks/useApi';
import { API_BASE } from '../../../lib/constants';

const ALL_VIEW_BY = [
  { label: 'Client',     value: 'client',    roles: ['website_admin'] },
  { label: 'Channel',    value: 'channel',   roles: ['website_admin', 'client_admin', 'user'] },
  { label: 'Input type', value: 'input_type', roles: ['website_admin', 'client_admin', 'user'] },
  { label: 'User',       value: 'user',      roles: ['website_admin', 'client_admin'] },
  { label: 'Team',       value: 'team',      roles: ['website_admin', 'client_admin'] },
];

/* Select styled as minimal underline with explicit dark background so the
   browser dropdown list doesn't pop up white. */
const selClass = [
  'border-0 border-b border-neutral-800',
  'bg-[#050505]',           /* same as page bg — prevents white flash */
  'pl-0 pr-5 py-1',
  'text-[12px] font-medium text-neutral-300',
  'outline-none appearance-none cursor-pointer',
  'hover:text-white hover:border-neutral-600 transition-colors',
].join(' ');

const CHEVRON = "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='9' height='5'%3E%3Cpath d='M1 1l3.5 3L8 1' stroke='%23525252' stroke-width='1.3' fill='none' stroke-linecap='round'/%3E%3C/svg%3E\")";
const selStyle = { backgroundImage: CHEVRON, backgroundRepeat: 'no-repeat', backgroundPosition: 'right 2px center' };

/* Inline label + select pair */
function FilterSelect({ label, value, onChange, children, disabled }) {
  return (
    <div className={`flex flex-col gap-0.5 ${disabled ? 'opacity-35 pointer-events-none' : ''}`}>
      <span className="text-[9px] font-bold uppercase tracking-[0.16em] text-neutral-600 select-none">{label}</span>
      <select className={selClass} style={selStyle} value={value} onChange={onChange} disabled={disabled}>
        {children}
      </select>
    </div>
  );
}

export default function FunnelFilterBar({ authUser, breakdown, filters, onBreakdownChange, onFiltersChange }) {
  const role    = authUser?.role || 'user';
  const isAdmin = role === 'website_admin';
  const isAdminOrClientAdmin = role === 'website_admin' || role === 'client_admin';

  const { data: opts } = useApi(`${API_BASE}/funnel/filter-options`, []);
  const options = opts || { clients: [], input_types: [], languages: [], channels: [], users: [], teams: [] };

  const allowedViewBy = ALL_VIEW_BY.filter((o) => o.roles.includes(role));

  const update = (key, value) => onFiltersChange({ ...filters, [key]: value || '' });
  const clear  = (key)        => onFiltersChange({ ...filters, [key]: '' });
  const reset  = ()           => onFiltersChange({ client: '', input_type: '', language: '', channel: '', user: '', team: '' });

  const active = Object.entries(filters).filter(([, v]) => v);

  return (
    <div className="pb-4 border-b border-neutral-900 space-y-2.5">
      {/* Row 1 */}
      <div className="flex flex-wrap items-end gap-x-6 gap-y-2">

        {/* View By */}
        <div className="flex items-center gap-2">
          <span className="text-[9.5px] font-bold uppercase tracking-[0.18em] text-neutral-600 select-none shrink-0">View by</span>
          <div className="flex gap-0.5">
            {allowedViewBy.map((item) => {
              const on = breakdown === item.value;
              return (
                <button
                  key={item.value}
                  onClick={() => onBreakdownChange(item.value)}
                  className={[
                    'relative px-3 py-1 rounded-full text-[11px] font-semibold transition-all duration-150',
                    on ? 'text-white' : 'text-neutral-500 hover:text-neutral-300',
                  ].join(' ')}
                >
                  {on && <span className="absolute inset-0 rounded-full bg-white/10 ring-1 ring-white/15" />}
                  <span className="relative">{item.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="h-4 w-px bg-neutral-800 shrink-0" />

        {/* Dropdowns */}
        <FilterSelect label="Input type" value={filters.input_type || ''} onChange={(e) => update('input_type', e.target.value)}>
          <option value="">All</option>
          {options.input_types.map((v) => <option key={v} value={v}>{v}</option>)}
        </FilterSelect>

        <FilterSelect label="Language" value={filters.language || ''} onChange={(e) => update('language', e.target.value)}>
          <option value="">All</option>
          {options.languages.map((v) => <option key={v} value={v}>{v}</option>)}
        </FilterSelect>

        <FilterSelect label="Channel" value={filters.channel || ''} onChange={(e) => update('channel', e.target.value)}>
          <option value="">All</option>
          {(options.channels || []).map((v) => <option key={v} value={v}>{v}</option>)}
        </FilterSelect>

        {isAdmin && (
          <FilterSelect label="Client" value={filters.client || ''} onChange={(e) => update('client', e.target.value)}>
            <option value="">All</option>
            {options.clients.map((v) => <option key={v} value={v}>{v}</option>)}
          </FilterSelect>
        )}

        {isAdminOrClientAdmin && (
          <FilterSelect label="User" value={filters.user || ''} onChange={(e) => update('user', e.target.value)}>
            <option value="">All</option>
            {(options.users || []).map((v) => <option key={v} value={v}>{v}</option>)}
          </FilterSelect>
        )}

        {isAdminOrClientAdmin && (
          <FilterSelect label="Team" value={filters.team || ''} onChange={(e) => update('team', e.target.value)}>
            <option value="">All</option>
            {(options.teams || []).map((v) => <option key={v} value={v}>{v}</option>)}
          </FilterSelect>
        )}

        <div className="flex-1" />

        <span className="text-[9.5px] font-semibold tracking-wide text-neutral-700 uppercase shrink-0 self-center">
          {role.replace(/_/g, ' ')}
        </span>

        {active.length > 0 && (
          <button onClick={reset} className="text-[10.5px] font-medium text-neutral-600 hover:text-neutral-300 transition-colors underline underline-offset-2 self-center">
            Reset
          </button>
        )}
      </div>

      {/* Active pills */}
      {active.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {active.map(([key, value]) => (
            <span key={key} className="inline-flex items-center gap-1 rounded-full bg-white/5 border border-white/[0.08] px-2.5 py-0.5 text-[10.5px] font-medium text-neutral-400">
              <span className="text-neutral-600">{key.replace('_', ' ')}:</span>
              {value}
              <button onClick={() => clear(key)} className="ml-0.5 text-neutral-600 hover:text-neutral-300 transition-colors">
                <X size={9} />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
