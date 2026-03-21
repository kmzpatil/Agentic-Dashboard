import React from 'react';
import { X } from 'lucide-react';
import { useApi } from '../../../hooks/useApi';
import { API_BASE } from '../../../lib/constants';

const ALL_VIEW_BY = [
  { label: 'Client',     value: 'client',    roles: ['website_admin'] },
  { label: 'Channel',    value: 'channel',   roles: ['website_admin', 'client_admin', 'user'] },
  { label: 'Input type', value: 'input_type', roles: ['website_admin', 'client_admin', 'user'] },
  { label: 'Output type', value: 'output_type', roles: ['website_admin', 'client_admin', 'user'] },
  { label: 'User',       value: 'user',      roles: ['website_admin', 'client_admin'] },
  { label: 'Team',       value: 'team',      roles: ['website_admin', 'client_admin'] },
];

function FilterSelect({ label, value, options, onChange, disabled }) {
  const [open, setOpen] = React.useState(false);
  const ref = React.useRef(null);

  React.useEffect(() => {
    if (!open) return undefined;
    const handleClickOutside = (event) => {
      if (ref.current && !ref.current.contains(event.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [open]);

  const selectedLabel = React.useMemo(() => {
    const selected = options.find((item) => item.value === value);
    return selected ? selected.label : 'All';
  }, [options, value]);

  const handleSelect = (nextValue) => {
    onChange(nextValue);
    setOpen(false);
  };

  return (
    <div ref={ref} className={`relative w-[100px] xl:w-[108px] 2xl:w-[116px] shrink-0 ${disabled ? 'opacity-45' : ''}`}>
      <span className="mb-0.5 block text-[9px] font-semibold uppercase tracking-[0.1em] text-neutral-400 select-none">{label}</span>
      <button
        type="button"
        onClick={() => { if (!disabled) setOpen((prev) => !prev); }}
        disabled={disabled}
        className={[
          'w-full h-[30px] rounded-lg border px-2.5',
          'flex items-center justify-between gap-2',
          'text-[12px] font-medium transition-colors',
          disabled
            ? 'border-neutral-800 bg-[#0b0b0b] text-neutral-400 cursor-not-allowed'
            : 'border-neutral-800 bg-[#0b0b0b] text-neutral-200 hover:border-neutral-700 hover:bg-[#111111]',
        ].join(' ')}
      >
        <span className="truncate text-left">{selectedLabel}</span>
        <svg
          width="10"
          height="6"
          viewBox="0 0 10 6"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`shrink-0 transition-transform ${open ? 'rotate-180 text-red-400' : 'text-neutral-500'}`}
        >
          <path d="M1 1L5 5L9 1" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      </button>

      {open && !disabled && (
        <div className="absolute left-0 right-0 mt-2 z-50 rounded-xl border border-neutral-800 bg-[#0f0f0f] shadow-[0_18px_40px_rgba(0,0,0,0.45)] p-1 max-h-[260px] overflow-y-auto">
          {options.map((item) => {
            const active = item.value === value;
            return (
              <button
                key={item.value || 'all'}
                type="button"
                onClick={() => handleSelect(item.value)}
                className={[
                  'w-full rounded-lg px-2 py-1.5 text-left text-[12px] transition-colors',
                  active
                    ? 'bg-red-500/12 text-red-300'
                    : 'text-neutral-300 hover:bg-neutral-800 hover:text-white',
                ].join(' ')}
              >
                <span className="truncate block">{item.label}</span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function FunnelFilterBar({ authUser, breakdown, filters, onBreakdownChange, onFiltersChange }) {
  const role    = authUser?.role || 'user';
  const isAdmin = role === 'website_admin';
  const isAdminOrClientAdmin = role === 'website_admin' || role === 'client_admin';

  const { data: opts, loading: optionsLoading, error: optionsError } = useApi(`${API_BASE}/funnel/filter-options`, []);
  const options = opts || { clients: [], input_types: [], languages: [], channels: [], users: [], teams: [] };
  const filtersDisabled = Boolean(optionsError) || optionsLoading;

  const allowedViewBy = ALL_VIEW_BY.filter((o) => o.roles.includes(role));

  const update = (key, value) => onFiltersChange({ ...filters, [key]: value || '' });
  const clear  = (key)        => onFiltersChange({ ...filters, [key]: '' });
  const reset  = ()           => onFiltersChange({ client: '', input_type: '', language: '', channel: '', user: '', team: '' });

  const FILTER_ORDER = ['client', 'channel', 'input_type', 'user', 'team', 'language'];
  const active = FILTER_ORDER
    .filter((key) => filters[key])
    .map((key) => [key, filters[key]]);

  return (
    <div className="pb-3 border-b border-neutral-900 space-y-2">
      {/* Row 1 */}
      <div className="flex flex-nowrap items-end gap-3">

        {/* View By */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-[10.5px] font-bold uppercase tracking-[0.12em] text-neutral-500 select-none shrink-0">View by</span>
          <div className="flex gap-0.5 shrink-0">
            {allowedViewBy.map((item) => {
              const on = breakdown === item.value;
              return (
                <button
                  key={item.value}
                  onClick={() => onBreakdownChange(item.value)}
                  className={[
                    'relative px-2.5 py-1 rounded-full text-[12px] font-semibold transition-all duration-150',
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

        <div className="flex flex-nowrap items-end gap-1.5 flex-1 min-w-0">

        {/* Dropdowns (ordered to match View by) */}
        {isAdmin && (
          <FilterSelect
            label="Client"
            value={filters.client || ''}
            onChange={(next) => update('client', next)}
            disabled={filtersDisabled}
            options={[
              { label: 'All', value: '' },
              ...options.clients.map((v) => ({ label: v, value: v })),
            ]}
          />
        )}

        <FilterSelect
          label="Channel"
          value={filters.channel || ''}
          onChange={(next) => update('channel', next)}
          disabled={filtersDisabled}
          options={[
            { label: 'All', value: '' },
            ...(options.channels || []).map((v) => ({ label: v, value: v })),
          ]}
        />

        <FilterSelect
          label="Input type"
          value={filters.input_type || ''}
          onChange={(next) => update('input_type', next)}
          disabled={filtersDisabled}
          options={[
            { label: 'All', value: '' },
            ...options.input_types.map((v) => ({ label: v, value: v })),
          ]}
        />

        {isAdminOrClientAdmin && (
          <FilterSelect
            label="User"
            value={filters.user || ''}
            onChange={(next) => update('user', next)}
            disabled={filtersDisabled}
            options={[
              { label: 'All', value: '' },
              ...(options.users || []).map((v) => ({ label: v, value: v })),
            ]}
          />
        )}

        {isAdminOrClientAdmin && (
          <FilterSelect
            label="Team"
            value={filters.team || ''}
            onChange={(next) => update('team', next)}
            disabled={filtersDisabled}
            options={[
              { label: 'All', value: '' },
              ...(options.teams || []).map((v) => ({ label: v, value: v })),
            ]}
          />
        )}

        <FilterSelect
          label="Language"
          value={filters.language || ''}
          onChange={(next) => update('language', next)}
          disabled={filtersDisabled}
          options={[
            { label: 'All', value: '' },
            ...options.languages.map((v) => ({ label: v, value: v })),
          ]}
        />

        </div>

        <span className="text-[11px] font-semibold tracking-wide text-neutral-400 uppercase shrink-0 self-center whitespace-nowrap">
          {role.replace(/_/g, ' ')}
        </span>

        {active.length > 0 && (
          <button onClick={reset} className="text-[12px] font-medium text-neutral-500 hover:text-neutral-200 transition-colors underline underline-offset-2 self-center">
            Reset
          </button>
        )}
      </div>

      {/* Active pills */}
      {optionsError && (
        <div className="rounded-lg border border-amber-600/30 bg-amber-500/10 px-3 py-2 text-[11px] text-amber-300">
          Filter options are temporarily unavailable. Retry in a moment.
        </div>
      )}

      {active.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {active.map(([key, value]) => (
            <span key={key} className="inline-flex items-center gap-1 rounded-full bg-white/5 border border-white/[0.08] px-2.5 py-0.5 text-[10.5px] font-medium text-neutral-400">
              <span className="text-neutral-400">{key.replace('_', ' ')}:</span>
              {value}
              <button onClick={() => clear(key)} className="ml-0.5 text-neutral-400 hover:text-neutral-300 transition-colors">
                <X size={9} />
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
