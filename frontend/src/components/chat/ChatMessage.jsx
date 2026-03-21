import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChevronDown, ChevronRight, Database, Activity } from 'lucide-react';
import { isReportHtml, cleanReportHtml } from '../../lib/reportXmlParser';
import ReportRenderer from '../reports/ReportRenderer';

const markdownComponents = {
  p:  ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-1">{children}</ol>,
  li: ({ children }) => <li className="text-[13px]">{children}</li>,
  strong: ({ children }) => <strong className="font-bold text-white">{children}</strong>,
  code: ({ inline, children }) =>
    inline
      ? <code className="bg-[#0A0A0A] px-1.5 py-0.5 rounded text-[11px] text-amber-300 font-mono">{children}</code>
      : <pre className="bg-[#0A0A0A] p-3 rounded-lg overflow-x-auto my-2 text-[11px] text-neutral-300 font-mono"><code>{children}</code></pre>,
  h3: ({ children }) => <h3 className="font-bold text-white text-sm mt-3 mb-1">{children}</h3>,
  h4: ({ children }) => <h4 className="font-bold text-neutral-200 text-[13px] mt-2 mb-1">{children}</h4>,
  table: ({ children }) => <div className="overflow-x-auto my-2"><table className="text-[11px] border-collapse w-full">{children}</table></div>,
  th: ({ children }) => <th className="border border-neutral-700 px-2 py-1 text-left text-neutral-300 bg-[#0A0A0A]">{children}</th>,
  td: ({ children }) => <td className="border border-neutral-800 px-2 py-1 text-neutral-400">{children}</td>,
};

function ActivityBlock({ actions }) {
  const [open, setOpen] = useState(false);
  if (!actions || actions.length === 0) return null;
  return (
    <div className="mt-3 pt-3 border-t border-neutral-800">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1.5 text-[10px] font-bold text-neutral-500 uppercase tracking-wider hover:text-neutral-300 transition-colors"
      >
        <Activity size={12} />
        Agent activity ({actions.length} steps)
        {open ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
      </button>
      {open && (
        <div className="mt-2 space-y-1">
          {actions.map((action, i) => (
            <div key={i} className="text-[11px] text-neutral-500 flex items-start gap-2">
              <span className="text-neutral-400 shrink-0 w-4 text-right">{i + 1}.</span>
              <span>{action}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DataBlock({ chartData }) {
  if (!chartData || Object.keys(chartData).length === 0) return null;
  return (
    <div className="mt-3 pt-3 border-t border-neutral-800">
      <div className="text-[10px] font-bold text-neutral-500 uppercase tracking-wider mb-2 flex items-center gap-1.5">
        <Database size={11} /> Returned datasets
      </div>
      <div className="space-y-1">
        {Object.entries(chartData).slice(0, 4).map(([name, rows]) => (
          <div key={name} className="text-[11px] text-neutral-400 flex items-center justify-between gap-3">
            <span className="truncate">{name}</span>
            <span className="text-neutral-500 whitespace-nowrap">{Array.isArray(rows) ? rows.length : 0} rows</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function ChatMessage({ msg, showActivity = false }) {
  if (msg.role === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-white text-black font-bold p-4 rounded-2xl rounded-tr-none text-sm w-4/5 shadow-[0_0_15px_rgba(255,255,255,0.1)]">
          {msg.content}
        </div>
      </div>
    );
  }

  // Check if this is a report message
  const reportRaw = msg.reportHtml || msg.report_html || msg.content || '';
  const isReport = msg.intent === 'report' || isReportHtml(reportRaw);

  if (isReport) {
    const html = msg.reportHtml || msg.report_html || cleanReportHtml(reportRaw);
    if (html) {
      return (
        <div>
          <ReportRenderer reportHtml={html} />
          {showActivity && <ActivityBlock actions={msg.actions} />}
        </div>
      );
    }
  }

  return (
    <div>
      <div className="bg-[#161616] text-neutral-200 p-4 rounded-2xl rounded-tl-none text-sm w-5/6 shadow-sm border border-neutral-800 hover:border-neutral-700 transition-colors">
        <div className="prose-sm">
          <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
            {msg.content || ''}
          </ReactMarkdown>
        </div>
        <DataBlock chartData={msg.chartData} />
        {showActivity && <ActivityBlock actions={msg.actions} />}
      </div>
    </div>
  );
}
