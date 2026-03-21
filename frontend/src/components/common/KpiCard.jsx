import React from 'react';
import { Line } from 'react-chartjs-2';
import { X, Plus, Pencil } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler
);

export default function KpiCard({ title, value, subtitle, trendData, onRemove, onAdd, onEdit, onClick }) {
  // Determine if trend is positive or negative for color
  const isTrendPositive = trendData && trendData.length > 0 && trendData[trendData.length - 1] >= trendData[0];
  const lineColor = isTrendPositive ? '#10b981' : '#ef4444'; // Green or Red

  const chartData = trendData ? {
    labels: trendData.map((_, i) => i.toString()),
    datasets: [
      {
        data: trendData,
        borderColor: lineColor,
        borderWidth: 2,
        tension: 0.4,
        pointRadius: 0,
        pointHoverRadius: 0,
        fill: true,
        backgroundColor: (context) => {
          const ctx = context.chart.ctx;
          const gradient = ctx.createLinearGradient(0, 0, 0, context.chart.height);
          gradient.addColorStop(0, `${lineColor}40`); // 40 is hex for 25% opacity
          gradient.addColorStop(1, `${lineColor}00`);
          return gradient;
        }
      }
    ]
  } : null;

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { enabled: false }
    },
    scales: {
      x: { display: false },
      y: { display: false, min: trendData ? Math.min(...trendData) * 0.9 : 0 }
    },
    interaction: {
      mode: 'index',
      intersect: false,
    },
  };

  const actions = [];
  if (onAdd) {
    actions.push({
      key: 'add',
      label: 'Add KPI',
      icon: <Plus size={14} />,
      onClick: onAdd,
      tone: 'hover:text-emerald-300 hover:border-emerald-500/40 hover:bg-emerald-500/10',
    });
  }
  if (onEdit) {
    actions.push({
      key: 'edit',
      label: 'Edit KPI',
      icon: <Pencil size={13} />,
      onClick: onEdit,
      tone: 'hover:text-sky-300 hover:border-sky-500/40 hover:bg-sky-500/10',
    });
  }
  if (onRemove) {
    actions.push({
      key: 'remove',
      label: 'Remove KPI',
      icon: <X size={14} />,
      onClick: onRemove,
      tone: 'hover:text-red-300 hover:border-red-500/40 hover:bg-red-500/10',
    });
  }

  const isInteractive = Boolean(onClick);

  return (
    <div 
      className={[
        'relative rounded-xl border bg-[#111317] p-4 transition-colors flex flex-col justify-between h-full',
        isInteractive
          ? 'cursor-pointer border-neutral-800 hover:border-neutral-600'
          : 'border-neutral-800 hover:border-neutral-700',
      ].join(' ')}
      onClick={onClick}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="text-[10.5px] font-bold uppercase tracking-[0.14em] text-neutral-400 mb-1.5">
            {title}
          </div>
          <div className="text-[30px] font-black leading-none tracking-tight text-white">
            {value}
          </div>
          <div className="mt-2.5 text-[12.5px] leading-snug text-neutral-400">
            {subtitle}
          </div>
        </div>
        {trendData && (
          <div className="w-[92px] h-[64px] shrink-0">
            <Line data={chartData} options={chartOptions} />
          </div>
        )}
      </div>

      {actions.length > 0 && (
        <div className="mt-3.5 flex items-center justify-end gap-1.5">
          {actions.map((action) => (
            <button
              key={action.key}
              title={action.label}
              aria-label={action.label}
              onClick={(event) => {
                event.stopPropagation();
                action.onClick?.();
              }}
              className={[
                'inline-flex h-7 w-7 items-center justify-center rounded-full border',
                'border-neutral-700 bg-[#0f1012] text-neutral-400 transition-colors',
                action.tone,
              ].join(' ')}
            >
              {action.icon}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
