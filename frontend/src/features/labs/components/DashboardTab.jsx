import React, { useMemo } from 'react';
import { Line, Doughnut, Bar } from 'react-chartjs-2';

const CHART_FONT_COLOR = '#a3a3a3';
const GRID_COLOR = 'rgba(64, 64, 64, 0.4)';

function chartOptions(title, extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top', labels: { color: CHART_FONT_COLOR, font: { size: 10 }, boxWidth: 12 } },
      title: { display: !!title, text: title, color: '#fff', font: { size: 12, weight: 'bold' } },
    },
    scales: {
      x: { ticks: { color: CHART_FONT_COLOR, font: { size: 9 }, maxTicksLimit: 10 }, grid: { color: GRID_COLOR } },
      y: { ticks: { color: CHART_FONT_COLOR, font: { size: 9 } }, grid: { color: GRID_COLOR }, beginAtZero: true, ...extra },
    },
  };
}

function doughnutOptions(title) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'right', labels: { color: CHART_FONT_COLOR, font: { size: 10 }, boxWidth: 10, padding: 8 } },
      title: { display: !!title, text: title, color: '#fff', font: { size: 12, weight: 'bold' } },
    },
  };
}

const CATEGORY_COLORS = {
  'Completeness': '#38bdf8',
  'Validity': '#f59e0b',
  'Referential Integrity': '#ef4444',
  'Timeliness': '#a78bfa',
  'Consistency': '#fb923c',
  'Business Logic': '#f43f5e',
  'Other': '#6b7280',
};

export default function DashboardTab({ dqa }) {
  const { timeseries, errorDist, stageScores } = dqa;

  // Quality time-series line chart
  const tsData = useMemo(() => {
    const labels = (timeseries?.labels || []).map((l) => l?.substring(11, 19) || '');
    return {
      labels,
      datasets: [
        { label: 'Upload', data: timeseries?.upload || [], borderColor: '#38bdf8', backgroundColor: 'rgba(56,189,248,0.1)', tension: 0.3, pointRadius: 0, borderWidth: 2, fill: true },
        { label: 'Processing', data: timeseries?.processing || [], borderColor: '#a78bfa', backgroundColor: 'rgba(167,139,250,0.1)', tension: 0.3, pointRadius: 0, borderWidth: 2, fill: true },
        { label: 'Publishing', data: timeseries?.publishing || [], borderColor: '#34d399', backgroundColor: 'rgba(52,211,153,0.1)', tension: 0.3, pointRadius: 0, borderWidth: 2, fill: true },
      ],
    };
  }, [timeseries]);

  // Error distribution doughnut
  const categoryData = useMemo(() => {
    const cats = errorDist?.by_category || {};
    const labels = Object.keys(cats);
    return {
      labels,
      datasets: [{
        data: Object.values(cats),
        backgroundColor: labels.map((l) => CATEGORY_COLORS[l] || '#6b7280'),
        borderWidth: 0,
      }],
    };
  }, [errorDist]);

  // Top error codes horizontal bar
  const topCodesData = useMemo(() => {
    const codes = (errorDist?.by_code || []).slice(0, 10);
    return {
      labels: codes.map((c) => c.code),
      datasets: [{
        label: 'Count',
        data: codes.map((c) => c.count),
        backgroundColor: '#ef4444',
        borderRadius: 4,
      }],
    };
  }, [errorDist]);

  // Latency histogram
  const latencyData = useMemo(() => {
    const buckets = dqa.funnel ? {} : {};
    // We'll fetch this separately, for now use stub
    return null;
  }, []);

  // Per-stage error counts
  const stageErrorData = useMemo(() => {
    const stages = errorDist?.by_stage || {};
    return {
      labels: Object.keys(stages),
      datasets: [{
        label: 'Errors',
        data: Object.values(stages),
        backgroundColor: ['#38bdf8', '#a78bfa', '#34d399', '#f59e0b'],
        borderRadius: 4,
      }],
    };
  }, [errorDist]);

  return (
    <div className="space-y-6">
      {/* Quality time-series */}
      <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5">
        <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400 mb-4">
          Quality Score Trends
        </h3>
        <div className="h-[280px]">
          {tsData.labels.length > 0 ? (
            <Line data={tsData} options={chartOptions(null, { max: 100 })} />
          ) : (
            <div className="flex items-center justify-center h-full text-neutral-600 text-sm">
              Waiting for data...
            </div>
          )}
        </div>
      </div>

      {/* Two-column row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Error distribution by category */}
        <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5">
          <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400 mb-4">
            Error Distribution by Category
          </h3>
          <div className="h-[240px]">
            {categoryData.labels.length > 0 ? (
              <Doughnut data={categoryData} options={doughnutOptions(null)} />
            ) : (
              <div className="flex items-center justify-center h-full text-neutral-600 text-sm">
                No errors yet
              </div>
            )}
          </div>
          <div className="mt-3 text-center text-[11px] text-neutral-500">
            Total errors: {errorDist?.total_errors ?? 0}
          </div>
        </div>

        {/* Errors by stage */}
        <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5">
          <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400 mb-4">
            Errors by Pipeline Stage
          </h3>
          <div className="h-[240px]">
            {stageErrorData.labels.length > 0 ? (
              <Bar data={stageErrorData} options={chartOptions(null)} />
            ) : (
              <div className="flex items-center justify-center h-full text-neutral-600 text-sm">
                No errors yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Top offending error codes */}
      <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5">
        <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400 mb-4">
          Top Error Codes
        </h3>
        <div className="h-[300px]">
          {topCodesData.labels.length > 0 ? (
            <Bar
              data={topCodesData}
              options={{
                ...chartOptions(null),
                indexAxis: 'y',
                plugins: {
                  ...chartOptions(null).plugins,
                  legend: { display: false },
                },
              }}
            />
          ) : (
            <div className="flex items-center justify-center h-full text-neutral-600 text-sm">
              No errors yet
            </div>
          )}
        </div>
      </div>

      {/* Processing latency */}
      <div className="bg-[#0E0E0E] border border-neutral-800 rounded-2xl p-5">
        <h3 className="text-sm font-bold tracking-widest uppercase text-neutral-400 mb-4">
          Processing Latency Distribution
        </h3>
        <LatencyHistogram dqa={dqa} />
      </div>
    </div>
  );
}

function LatencyHistogram({ dqa }) {
  const [data, setData] = React.useState(null);

  React.useEffect(() => {
    fetch(`${import.meta.env.VITE_API_BASE || '/api'}/labs/simulator/quality/latency`)
      .then((r) => r.ok ? r.json() : null)
      .then((d) => setData(d))
      .catch(() => {});
  }, [dqa.stageScores]); // re-fetch when scores change

  const chartData = React.useMemo(() => {
    if (!data?.buckets) return null;
    const labels = Object.keys(data.buckets);
    return {
      labels,
      datasets: [{
        label: 'Assets',
        data: Object.values(data.buckets),
        backgroundColor: '#a78bfa',
        borderRadius: 4,
      }],
    };
  }, [data]);

  if (!chartData) {
    return <div className="h-[200px] flex items-center justify-center text-neutral-600 text-sm">Loading...</div>;
  }

  return (
    <div className="h-[200px]">
      <Bar data={chartData} options={{
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: CHART_FONT_COLOR, font: { size: 9 } }, grid: { color: GRID_COLOR } },
          y: { ticks: { color: CHART_FONT_COLOR, font: { size: 9 } }, grid: { color: GRID_COLOR }, beginAtZero: true },
        },
      }} />
    </div>
  );
}
