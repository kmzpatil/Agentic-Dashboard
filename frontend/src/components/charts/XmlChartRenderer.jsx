import React, { useMemo } from 'react';
import { BarChart3, PieChart, TrendingUp, Hash } from 'lucide-react';

function parseXml(xmlString) {
  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xmlString, 'text/xml');
    const error = doc.querySelector('parsererror');
    if (error) return null;
    return doc;
  } catch {
    return null;
  }
}

function getAttr(el, name, fallback = '') {
  return el?.getAttribute(name) || fallback;
}

function KpiWidget({ widget, data }) {
  const metric = getAttr(widget, 'metric');
  const title = getAttr(widget, 'title', 'Metric');
  const value = data?.[0]?.[metric] ?? '—';

  return (
    <div className="bg-[#111111] border border-neutral-800 rounded-xl p-5 flex flex-col items-center justify-center">
      <div className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider mb-2">{title}</div>
      <div className="text-3xl font-bold text-white">{typeof value === 'number' ? value.toLocaleString() : String(value)}</div>
    </div>
  );
}

function BarChartWidget({ widget, data }) {
  const xField = getAttr(widget, 'x-field');
  const yFieldsStr = getAttr(widget, 'y-fields');
  const title = getAttr(widget, 'title', 'Chart');
  const yFields = yFieldsStr.split(',').map(f => f.trim()).filter(Boolean);

  if (!data || data.length === 0 || !xField || yFields.length === 0) {
    return <EmptyChart title={title} />;
  }

  const maxVal = Math.max(...data.flatMap(row => yFields.map(f => Number(row[f]) || 0)), 1);

  return (
    <div className="bg-[#111111] border border-neutral-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4">
        <BarChart3 size={14} className="text-blue-400" />
        <span className="text-[13px] font-semibold text-neutral-300">{title}</span>
      </div>
      <div className="flex items-end gap-1 h-[200px]">
        {data.slice(0, 20).map((row, i) => (
          <div key={i} className="flex-1 flex flex-col items-center justify-end h-full min-w-0">
            {yFields.map((yf, yi) => {
              const val = Number(row[yf]) || 0;
              const pct = (val / maxVal) * 100;
              const colors = ['bg-blue-500', 'bg-emerald-500', 'bg-amber-500', 'bg-purple-500'];
              return (
                <div
                  key={yi}
                  className={`w-full max-w-[32px] ${colors[yi % colors.length]} rounded-t-sm transition-all`}
                  style={{ height: `${Math.max(pct, 2)}%` }}
                  title={`${yf}: ${val}`}
                />
              );
            })}
            <div className="text-[9px] text-neutral-600 mt-1 truncate w-full text-center" title={String(row[xField])}>
              {String(row[xField] ?? '').slice(0, 8)}
            </div>
          </div>
        ))}
      </div>
      {yFields.length > 1 && (
        <div className="flex gap-3 mt-3">
          {yFields.map((yf, i) => {
            const colors = ['bg-blue-500', 'bg-emerald-500', 'bg-amber-500', 'bg-purple-500'];
            return (
              <div key={yf} className="flex items-center gap-1.5 text-[10px] text-neutral-500">
                <div className={`w-2 h-2 rounded-sm ${colors[i % colors.length]}`} />
                {yf.replace(/_/g, ' ')}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function LineChartWidget({ widget, data }) {
  const xField = getAttr(widget, 'x-field');
  const yFieldsStr = getAttr(widget, 'y-fields');
  const title = getAttr(widget, 'title', 'Chart');
  const yFields = yFieldsStr.split(',').map(f => f.trim()).filter(Boolean);

  if (!data || data.length === 0 || !xField || yFields.length === 0) {
    return <EmptyChart title={title} />;
  }

  const maxVal = Math.max(...data.flatMap(row => yFields.map(f => Number(row[f]) || 0)), 1);
  const w = 100;
  const h = 50;
  const pad = 2;

  return (
    <div className="bg-[#111111] border border-neutral-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-4">
        <TrendingUp size={14} className="text-emerald-400" />
        <span className="text-[13px] font-semibold text-neutral-300">{title}</span>
      </div>
      <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-[200px]" preserveAspectRatio="none">
        {yFields.map((yf, yi) => {
          const colors = ['#3b82f6', '#10b981', '#f59e0b', '#a855f7'];
          const points = data.map((row, i) => {
            const x = pad + (i / Math.max(data.length - 1, 1)) * (w - pad * 2);
            const y = h - pad - ((Number(row[yf]) || 0) / maxVal) * (h - pad * 2);
            return `${x},${y}`;
          }).join(' ');
          return (
            <polyline
              key={yi}
              points={points}
              fill="none"
              stroke={colors[yi % colors.length]}
              strokeWidth="0.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          );
        })}
      </svg>
      <div className="flex justify-between mt-2 text-[9px] text-neutral-600">
        <span>{String(data[0]?.[xField] ?? '').slice(0, 10)}</span>
        <span>{String(data[data.length - 1]?.[xField] ?? '').slice(0, 10)}</span>
      </div>
    </div>
  );
}

function PieChartWidget({ widget, data }) {
  const nameField = getAttr(widget, 'name-field');
  const valueField = getAttr(widget, 'value-field');
  const title = getAttr(widget, 'title', 'Chart');

  if (!data || data.length === 0) return <EmptyChart title={title} />;

  const slices = data.slice(0, 8).map(row => ({
    label: String(row[nameField] || ''),
    value: Number(row[valueField]) || 0,
  }));
  const total = slices.reduce((s, d) => s + d.value, 0) || 1;
  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#a855f7', '#ef4444', '#06b6d4', '#ec4899', '#84cc16'];

  let cumAngle = 0;
  const paths = slices.map((slice, i) => {
    const angle = (slice.value / total) * 360;
    const startAngle = cumAngle;
    cumAngle += angle;
    const r = 40;
    const cx = 50, cy = 50;
    const startRad = (startAngle - 90) * (Math.PI / 180);
    const endRad = (startAngle + angle - 90) * (Math.PI / 180);
    const largeArc = angle > 180 ? 1 : 0;
    const x1 = cx + r * Math.cos(startRad);
    const y1 = cy + r * Math.sin(startRad);
    const x2 = cx + r * Math.cos(endRad);
    const y2 = cy + r * Math.sin(endRad);
    const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 ${largeArc} 1 ${x2} ${y2} Z`;
    return <path key={i} d={d} fill={colors[i % colors.length]} opacity={0.85} />;
  });

  return (
    <div className="bg-[#111111] border border-neutral-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-3">
        <PieChart size={14} className="text-purple-400" />
        <span className="text-[13px] font-semibold text-neutral-300">{title}</span>
      </div>
      <div className="flex items-center gap-4">
        <svg viewBox="0 0 100 100" className="w-[140px] h-[140px] shrink-0">
          {paths}
        </svg>
        <div className="flex-1 space-y-1.5">
          {slices.map((s, i) => (
            <div key={i} className="flex items-center gap-2 text-[11px]">
              <div className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ backgroundColor: colors[i % colors.length] }} />
              <span className="text-neutral-400 truncate flex-1">{s.label}</span>
              <span className="text-neutral-500 font-mono">{((s.value / total) * 100).toFixed(1)}%</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function EmptyChart({ title }) {
  return (
    <div className="bg-[#111111] border border-neutral-800 rounded-xl p-6 flex flex-col items-center justify-center text-center">
      <Hash size={20} className="text-neutral-700 mb-2" />
      <div className="text-[12px] text-neutral-500">{title || 'No data to visualize'}</div>
    </div>
  );
}

export default function XmlChartRenderer({ xmlString, data }) {
  const widgets = useMemo(() => {
    if (!xmlString) return [];
    const doc = parseXml(xmlString);
    if (!doc) return [];
    return Array.from(doc.querySelectorAll('widget'));
  }, [xmlString]);

  if (widgets.length === 0) return null;

  const dataArray = useMemo(() => {
    if (!data) return [];
    if (Array.isArray(data)) return data;
    const vals = Object.values(data);
    for (const v of vals) {
      if (Array.isArray(v) && v.length > 0) return v;
    }
    return [];
  }, [data]);

  return (
    <div className="space-y-4">
      {widgets.map((widget, idx) => {
        const type = getAttr(widget, 'type');
        switch (type) {
          case 'kpi':
            return <KpiWidget key={idx} widget={widget} data={dataArray} />;
          case 'bar-chart':
            return <BarChartWidget key={idx} widget={widget} data={dataArray} />;
          case 'line-chart':
            return <LineChartWidget key={idx} widget={widget} data={dataArray} />;
          case 'pie-chart':
            return <PieChartWidget key={idx} widget={widget} data={dataArray} />;
          default:
            return <BarChartWidget key={idx} widget={widget} data={dataArray} />;
        }
      })}
    </div>
  );
}
