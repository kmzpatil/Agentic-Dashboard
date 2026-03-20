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

  return (
    <div 
      className={`relative bg-[#111111] rounded-xl p-5 border border-neutral-800 transition-colors flex flex-col justify-between h-full ${onClick ? 'cursor-pointer hover:border-neutral-500' : 'hover:border-neutral-600'}`}
      onClick={onClick}
    >
      {onRemove && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="absolute top-3 right-3 text-neutral-500 hover:text-red-400 transition-colors"
        >
          <X size={16} />
        </button>
      )}
      {onEdit && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          className={`absolute top-3 transition-colors text-neutral-500 hover:text-blue-400 ${onRemove ? 'right-8' : 'right-3'}`}
        >
          <Pencil size={14} />
        </button>
      )}
      {onAdd && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onAdd();
          }}
          className="absolute top-3 right-3 text-neutral-500 hover:text-white transition-colors"
        >
          <Plus size={16} />
        </button>
      )}
      
      <div className="flex justify-between items-start h-full">
        <div className="flex-1 flex flex-col justify-between h-full">
          <div>
            <div className="text-xs font-bold tracking-wider text-neutral-500 mb-1">{title}</div>
            <div className="text-3xl font-black text-white tracking-tight">{value}</div>
          </div>
          <div className="text-sm text-neutral-400 mt-2">{subtitle}</div>
        </div>
        
        {trendData && (
          <div className="w-24 h-16 ml-4 mt-2 shrink-0">
            <Line data={chartData} options={chartOptions} />
          </div>
        )}
      </div>
    </div>
  );
}
