import React, { useState, useRef } from 'react';
import {
  AlertTriangle,
  BarChart3,
  BookOpen,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Download,
  FileText,
  Info,
  Lightbulb,
  Loader2,
  TrendingUp,
} from 'lucide-react';
import jsPDF from 'jspdf';
import html2canvas from 'html2canvas';

const SEVERITY_STYLES = {
  critical: { bg: 'bg-red-950/30', border: 'border-red-800/40', text: 'text-red-300', icon: AlertTriangle, iconColor: 'text-red-400' },
  high:     { bg: 'bg-orange-950/20', border: 'border-orange-800/30', text: 'text-orange-300', icon: AlertTriangle, iconColor: 'text-orange-400' },
  medium:   { bg: 'bg-amber-950/20', border: 'border-amber-800/30', text: 'text-amber-300', icon: Info, iconColor: 'text-amber-400' },
  low:      { bg: 'bg-blue-950/20', border: 'border-blue-800/30', text: 'text-blue-300', icon: Info, iconColor: 'text-blue-400' },
  info:     { bg: 'bg-neutral-900/40', border: 'border-neutral-700/40', text: 'text-neutral-300', icon: Info, iconColor: 'text-neutral-400' },
};

const SECTION_ICONS = {
  trend: TrendingUp,
  breakdown: BarChart3,
  comparison: BarChart3,
  anomaly: AlertTriangle,
  forecast: TrendingUp,
};

function formatCellValue(value, format) {
  if (value === '' || value == null) return '—';
  switch (format) {
    case 'currency':
      return `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
    case 'percent':
      return `${Number(value).toFixed(1)}%`;
    case 'number':
      return Number(value).toLocaleString();
    default:
      return String(value);
  }
}

function FindingBadge({ finding }) {
  const style = SEVERITY_STYLES[finding.severity] || SEVERITY_STYLES.info;
  const Icon = style.icon;
  return (
    <div className={`flex items-start gap-2 rounded-lg ${style.bg} ${style.border} border px-3 py-2`}>
      <Icon size={13} className={`${style.iconColor} shrink-0 mt-0.5`} />
      <span className={`text-[13px] leading-relaxed ${style.text}`}>{finding.text}</span>
    </div>
  );
}

function DataTableView({ dataTable }) {
  if (!dataTable || !dataTable.columns?.length) return null;
  return (
    <div className="mt-4 rounded-xl border border-neutral-800 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead className="bg-[#0F0F0F]">
            <tr>
              {dataTable.columns.map(col => (
                <th key={col.field} className="px-3 py-2.5 text-left text-[10px] font-bold uppercase tracking-[0.18em] text-neutral-500">
                  {col.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {dataTable.rows.map((row, i) => (
              <tr key={i} className="border-t border-neutral-900 hover:bg-[#111111] transition-colors">
                {dataTable.columns.map(col => (
                  <td key={col.field} className="px-3 py-2 text-neutral-300 whitespace-nowrap font-mono text-[12px]">
                    {formatCellValue(row[col.field], col.format)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ChartPlaceholder({ chart }) {
  if (!chart) return null;
  return (
    <div className="mt-4 rounded-xl border border-neutral-800 bg-[#0D0D0D] p-5 flex flex-col items-center justify-center gap-2">
      <BarChart3 size={20} className="text-neutral-600" />
      <span className="text-[12px] text-neutral-500 font-semibold">{chart.title || 'Chart'}</span>
      <span className="text-[11px] text-neutral-600">
        {chart.chartType} — {chart.xColumn} vs {chart.yColumns}
      </span>
    </div>
  );
}

function ReportSection({ section, index }) {
  const [expanded, setExpanded] = useState(true);
  const SectionIcon = SECTION_ICONS[section.type] || BarChart3;
  const typeLabel = section.type.charAt(0).toUpperCase() + section.type.slice(1);

  return (
    <div className="rounded-2xl border border-neutral-800 bg-[#0C0C0C] overflow-hidden">
      <button
        onClick={() => setExpanded(e => !e)}
        className="flex w-full items-center gap-3 px-5 py-4 text-left hover:bg-[#111111] transition-colors"
      >
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-neutral-800/60">
          <SectionIcon size={14} className="text-neutral-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[14px] font-semibold text-white truncate">{section.heading}</div>
          <span className="text-[10px] font-bold uppercase tracking-[0.15em] text-neutral-600">{typeLabel} Analysis</span>
        </div>
        {expanded ? <ChevronDown size={14} className="text-neutral-600" /> : <ChevronRight size={14} className="text-neutral-600" />}
      </button>

      {expanded && (
        <div className="border-t border-neutral-800/60 px-5 py-4 space-y-4">
          <p className="text-[14px] leading-[1.8] text-neutral-300">{section.narrative}</p>

          <ChartPlaceholder chart={section.chart} />
          <DataTableView dataTable={section.dataTable} />

          {section.keyFindings?.length > 0 && (
            <div className="space-y-2 pt-2">
              <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-neutral-600 mb-2">Key Findings</div>
              {section.keyFindings.map((f, i) => (
                <FindingBadge key={i} finding={f} />
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function ReportRenderer({ report }) {
  const reportRef = useRef(null);
  const [exporting, setExporting] = useState(false);

  if (!report) return null;

  const handleExportPDF = async () => {
    if (!reportRef.current || exporting) return;
    setExporting(true);

    try {
      const element = reportRef.current;
      const canvas = await html2canvas(element, {
        scale: 2,
        useCORS: true,
        logging: false,
        backgroundColor: '#0B0B0B',
      });

      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = pdf.internal.pageSize.getHeight();
      
      const imgWidth = pdfWidth;
      const imgHeight = (canvas.height * pdfWidth) / canvas.width;
      
      let heightLeft = imgHeight;
      let position = 0;

      // Add the first page
      pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
      heightLeft -= pdfHeight;

      // Add extra pages if needed
      while (heightLeft > 0) {
        position = heightLeft - imgHeight;
        pdf.addPage();
        pdf.addImage(imgData, 'PNG', 0, position, imgWidth, imgHeight);
        heightLeft -= pdfHeight;
      }

      pdf.save(`${report.metadata.title.replace(/[^a-zA-Z0-9]/g, '_')}_report.pdf`);
    } catch (err) {
      console.error('PDF export failed:', err);
      // Fallback to text download
      handleDownloadText();
    } finally {
      setExporting(false);
    }
  };

  const handleDownloadText = () => {
    const text = [
      report.metadata.title,
      report.metadata.subtitle,
      `Date Range: ${report.metadata.dateRange}`,
      '',
      'EXECUTIVE SUMMARY',
      report.executiveSummary,
      '',
      ...report.sections.flatMap(s => [
        `--- ${s.heading} (${s.type}) ---`,
        s.narrative,
        ...(s.keyFindings || []).map(f => `  [${f.severity}] ${f.text}`),
        '',
      ]),
      'CONCLUSIONS',
      ...report.conclusions.map((c, i) => `${i + 1}. ${c}`),
      '',
      'RECOMMENDATIONS',
      ...report.recommendations.map(r => `${r.priority}. ${r.text}`),
    ].join('\n');

    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${report.metadata.title.replace(/[^a-zA-Z0-9]/g, '_')}_report.txt`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="max-w-[820px] space-y-6">
      {/* Header */}
      <div className="rounded-2xl border border-neutral-800 bg-gradient-to-br from-[#111111] to-[#0A0A0A] p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2.5 mb-3">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-red-500/10">
                <FileText size={16} className="text-red-400" />
              </div>
              <span className="text-[11px] font-bold uppercase tracking-[0.15em] text-red-400/80">Analytical Report</span>
            </div>
            <h1 className="text-xl font-bold text-white leading-tight">{report.metadata.title}</h1>
            {report.metadata.subtitle && (
              <p className="mt-1 text-[14px] text-neutral-400">{report.metadata.subtitle}</p>
            )}
            {report.metadata.dateRange && (
              <p className="mt-2 text-[12px] text-neutral-600">{report.metadata.dateRange}</p>
            )}
          </div>
          <div className="flex gap-2">
            <button
              onClick={handleExportPDF}
              disabled={exporting}
              className="flex items-center gap-1.5 rounded-xl border border-neutral-800 bg-[#0E0E0E] px-3 py-2 text-[12px] font-semibold text-neutral-400 transition-colors hover:border-neutral-700 hover:text-neutral-200 disabled:opacity-50"
            >
              {exporting ? (
                <Loader2 size={13} className="animate-spin" />
              ) : (
                <Download size={13} />
              )}
              {exporting ? 'Generating...' : 'PDF'}
            </button>
            <button
              onClick={handleDownloadText}
              className="flex items-center justify-center rounded-xl border border-neutral-800 bg-[#0E0E0E] px-3 py-2 text-[12px] font-semibold text-neutral-500 transition-colors hover:border-neutral-700 hover:text-neutral-300"
              title="Download as Text"
            >
              TXT
            </button>
          </div>
        </div>
      </div>

      <div ref={reportRef} className="space-y-6">

      {report.executiveSummary && (
        <div className="rounded-2xl border border-neutral-800 bg-[#0C0C0C] p-5">
          <div className="flex items-center gap-2 mb-3">
            <BookOpen size={14} className="text-blue-400" />
            <span className="text-[12px] font-bold uppercase tracking-[0.15em] text-neutral-500">Executive Summary</span>
          </div>
          <p className="text-[14px] leading-[1.85] text-neutral-200">{report.executiveSummary}</p>
        </div>
      )}

      {/* Sections */}
      {report.sections.map((section, i) => (
        <ReportSection key={i} section={section} index={i} />
      ))}

      {/* Conclusions */}
      {report.conclusions?.length > 0 && (
        <div className="rounded-2xl border border-neutral-800 bg-[#0C0C0C] p-5">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 size={14} className="text-emerald-400" />
            <span className="text-[12px] font-bold uppercase tracking-[0.15em] text-neutral-500">Conclusions</span>
          </div>
          <div className="space-y-2">
            {report.conclusions.map((c, i) => (
              <div key={i} className="flex items-start gap-2.5">
                <span className="text-[12px] font-bold text-neutral-600 mt-0.5 shrink-0 w-5 text-right">{i + 1}.</span>
                <p className="text-[14px] leading-[1.7] text-neutral-300">{c}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recommendations */}
      {report.recommendations?.length > 0 && (
        <div className="rounded-2xl border border-neutral-800 bg-[#0C0C0C] p-5">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb size={14} className="text-amber-400" />
            <span className="text-[12px] font-bold uppercase tracking-[0.15em] text-neutral-500">Recommendations</span>
          </div>
          <div className="space-y-3">
            {report.recommendations.map((r, i) => (
              <div key={i} className="flex items-start gap-3 rounded-xl border border-neutral-800/60 bg-[#0D0D0D] p-3">
                <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-amber-500/10 shrink-0">
                  <span className="text-[11px] font-bold text-amber-400">P{r.priority}</span>
                </div>
                <p className="text-[13px] leading-[1.7] text-neutral-300">{r.text}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  </div>
);
}
