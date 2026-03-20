import React, { useState } from 'react';
import { CheckCircle2, Download, FileText, Loader2 } from 'lucide-react';
import DOMPurify from 'dompurify';

/**
 * PDF styles — continuous-flow layout.
 * No page divs. The browser's print engine fills pages naturally.
 * page-break-inside:avoid on sections prevents content splitting.
 * position:fixed header repeats on every printed page.
 */
const PDF_CSS = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: -apple-system, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
    color: #1a1a1a; background: #fff;
    font-size: 11px; line-height: 1.5;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
    margin: 0; padding: 0;
  }
  @page { size: A4; margin: 18mm 16mm 16mm 16mm; }

  /* ── Fixed header repeats on every printed page ── */
  .report-page-header {
    position: fixed; top: 0; left: 0; right: 0;
    display: flex; align-items: center; gap: 8px;
    padding: 0 0 6px 0;
    border-bottom: 2px solid #ef4444;
    background: #fff;
    height: 24px;
  }
  .report-page-header .logo { font-size: 13px; font-weight: 800; color: #ef4444; letter-spacing: -0.02em; }
  .report-page-header .divider { width: 1px; height: 12px; background: #d1d5db; }
  .report-page-header .label { font-size: 8px; font-weight: 700; letter-spacing: 0.18em; text-transform: uppercase; color: #9ca3af; }

  /* ── Push content below fixed header + breathing room ── */
  .report { padding-top: 36px; }

  /* ── Footer space so content doesn't touch bottom edge ── */
  .report::after {
    content: '';
    display: block;
    height: 20px;
  }

  /* ── Cover ── */
  .cover-header { padding: 8px 0 10px 0; margin-bottom: 12px; }
  .report-badge {
    display: inline-block; font-size: 8px; font-weight: 700;
    letter-spacing: 0.18em; text-transform: uppercase;
    color: #dc2626; background: #fef2f2;
    padding: 2px 8px; border-radius: 8px; margin-bottom: 6px;
  }
  .report-title { font-size: 20px; font-weight: 800; color: #111; margin: 0 0 3px 0; line-height: 1.2; }
  .report-subtitle { font-size: 12px; color: #6b7280; margin: 0 0 6px 0; }
  .report-meta { display: flex; gap: 14px; font-size: 9px; color: #9ca3af; }

  /* ── Executive Summary ── */
  .executive-summary {
    background: #f0f7ff; border: 1px solid #dbeafe;
    border-radius: 6px; padding: 12px 14px; margin-bottom: 14px;
    page-break-inside: avoid;
  }
  .executive-summary h2 {
    font-size: 9px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.14em; color: #2563eb; margin: 0 0 6px 0;
  }
  .executive-summary p { font-size: 10.5px; color: #374151; margin: 0; line-height: 1.55; }

  /* ── Sections ── */
  .section {
    margin-bottom: 14px; padding-bottom: 12px;
    border-bottom: 1px solid #f3f4f6;
    page-break-inside: avoid;
  }
  .section:last-of-type { border-bottom: none; }
  .section-header {
    display: flex; align-items: center; gap: 7px;
    margin-bottom: 6px; padding-bottom: 4px;
    border-bottom: 1px solid #e5e7eb;
  }
  .section-type {
    font-size: 7px; font-weight: 700; letter-spacing: 0.14em;
    text-transform: uppercase; color: #6b7280; background: #f3f4f6;
    padding: 2px 6px; border-radius: 3px;
  }
  .section-header h3 { font-size: 12px; font-weight: 700; color: #111827; margin: 0; }
  .narrative { font-size: 10.5px; color: #374151; margin: 0 0 8px 0; line-height: 1.55; }

  /* ── Table ── */
  .data-table {
    width: 100%; border-collapse: collapse; font-size: 9px;
    margin: 8px 0; page-break-inside: avoid;
  }
  .data-table thead { background: #f9fafb; }
  .data-table th {
    text-align: left; padding: 4px 6px; font-size: 7px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.1em;
    color: #6b7280; border-bottom: 1px solid #d1d5db;
  }
  .data-table td {
    padding: 4px 6px; color: #374151;
    border-bottom: 1px solid #f3f4f6;
    font-variant-numeric: tabular-nums;
  }

  /* ── Charts — Horizontal Bar ── */
  .chart-container {
    margin: 8px 0; padding: 8px 10px;
    background: #fafbfc; border: 1px solid #f0f0f0; border-radius: 6px;
    page-break-inside: avoid;
  }
  .chart-title { font-size: 9px; font-weight: 700; color: #374151; margin-bottom: 6px; }
  .bar-chart-row { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; }
  .bar-chart-label {
    width: 110px; font-size: 8.5px; color: #6b7280; text-align: right;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex-shrink: 0;
  }
  .bar-chart-bar { height: 14px; border-radius: 3px; min-width: 3px; transition: width 0.3s; }
  .bar-chart-value { font-size: 8.5px; color: #374151; font-weight: 600; min-width: 40px; }

  /* ── Charts — Comparison Row ── */
  .comparison-row { display: flex; align-items: center; gap: 6px; margin-bottom: 3px; }

  /* ── Charts — Sparkline (vertical bars for trends) ── */
  .sparkline-row {
    display: flex; align-items: flex-end; gap: 2px;
    height: 60px; padding: 4px 0;
  }
  .sparkline-bar {
    flex: 1; min-width: 8px; border-radius: 2px 2px 0 0;
    transition: height 0.3s;
  }
  .sparkline-label {
    flex: 1; text-align: center;
    font-size: 7px; color: #9ca3af; margin-top: 2px;
  }
  .sparkline-labels {
    display: flex; gap: 2px;
  }

  /* ── Charts — Proportion Bar ── */
  .proportion-row {
    display: flex; height: 16px; border-radius: 4px; overflow: hidden;
    margin-bottom: 4px;
  }
  .proportion-segment { min-width: 2px; }
  .proportion-legend {
    display: flex; gap: 10px; flex-wrap: wrap; margin-top: 2px;
  }
  .proportion-legend span { font-size: 8px; color: #6b7280; display: flex; align-items: center; gap: 3px; }
  .legend-dot {
    display: inline-block; width: 7px; height: 7px; border-radius: 2px;
  }

  /* ── Findings ── */
  .findings { display: flex; flex-direction: column; gap: 4px; margin-top: 6px; }
  .finding {
    display: flex; align-items: flex-start; gap: 6px;
    padding: 5px 8px; border-radius: 4px; font-size: 9px;
    page-break-inside: avoid;
  }
  .finding-badge {
    font-size: 7px; font-weight: 700; letter-spacing: 0.08em;
    padding: 1px 5px; border-radius: 2px; white-space: nowrap;
    flex-shrink: 0; margin-top: 1px;
  }
  .finding-critical { background: #fef2f2; border: 1px solid #fecaca; color: #991b1b; }
  .finding-critical .finding-badge { background: #fee2e2; color: #dc2626; }
  .finding-high { background: #fff7ed; border: 1px solid #fed7aa; color: #9a3412; }
  .finding-high .finding-badge { background: #ffedd5; color: #ea580c; }
  .finding-medium { background: #fffbeb; border: 1px solid #fde68a; color: #92400e; }
  .finding-medium .finding-badge { background: #fef3c7; color: #d97706; }
  .finding-low { background: #eff6ff; border: 1px solid #bfdbfe; color: #1e40af; }
  .finding-low .finding-badge { background: #dbeafe; color: #2563eb; }
  .finding-info { background: #f9fafb; border: 1px solid #e5e7eb; color: #374151; }
  .finding-info .finding-badge { background: #f3f4f6; color: #6b7280; }

  /* ── Conclusions ── */
  .conclusions, .recommendations { margin-bottom: 14px; page-break-inside: avoid; }
  .conclusions h2, .recommendations h2 {
    font-size: 9px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.14em; color: #374151; margin: 0 0 6px 0;
    padding-bottom: 4px; border-bottom: 1px solid #e5e7eb;
  }
  .conclusions ol { margin: 0; padding-left: 14px; }
  .conclusions li { font-size: 10px; color: #374151; margin-bottom: 4px; line-height: 1.5; }
  .recommendation {
    display: flex; align-items: flex-start; gap: 8px;
    padding: 6px 10px; background: #f9fafb; border: 1px solid #e5e7eb;
    border-radius: 6px; margin-bottom: 5px; page-break-inside: avoid;
  }
  .priority-badge {
    display: flex; align-items: center; justify-content: center;
    width: 20px; height: 20px; border-radius: 4px;
    background: #fef3c7; color: #b45309;
    font-size: 8px; font-weight: 700; flex-shrink: 0;
  }
  .recommendation p { font-size: 10px; color: #374151; margin: 0; line-height: 1.5; }
`;

const PAGE_HEADER_HTML = '<div class="report-page-header"><span class="logo">FRAMMER AI</span><span class="divider"></span><span class="label">Analytics Report</span></div>';

function buildPdfDocument(reportHtml) {
  const sanitized = DOMPurify.sanitize(reportHtml, {
    USE_PROFILES: { html: true },
    FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed', 'form', 'input'],
    FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur', 'onchange', 'onsubmit', 'style'],
  });
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Frammer Report</title>
<style>${PDF_CSS}</style>
</head>
<body>
${PAGE_HEADER_HTML}
${sanitized}
</body>
</html>`;
}

export default function ReportRenderer({ reportHtml }) {
  const [downloading, setDownloading] = useState(false);
  const [downloaded, setDownloaded] = useState(false);

  if (!reportHtml) return null;

  const titleMatch = reportHtml.match(/<(?:h1)[^>]*>(.*?)<\/(?:h1)>/si);
  const reportTitle = titleMatch
    ? titleMatch[1].replace(/<[^>]+>/g, '').trim()
    : 'Analytical Report';

  const handleDownloadPdf = async () => {
    setDownloading(true);
    setDownloaded(false);
    try {
      const fullDoc = buildPdfDocument(reportHtml);

      const iframe = document.createElement('iframe');
      iframe.style.cssText = 'position:fixed;top:0;left:0;width:0;height:0;border:none;visibility:hidden;';
      document.body.appendChild(iframe);

      const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
      iframeDoc.open();
      iframeDoc.write(fullDoc);
      iframeDoc.close();

      await new Promise((resolve) => {
        if (iframe.contentWindow.document.readyState === 'complete') resolve();
        else iframe.contentWindow.addEventListener('load', resolve);
      });
      await new Promise((r) => setTimeout(r, 300));

      iframe.contentWindow.focus();
      iframe.contentWindow.print();

      setTimeout(() => { try { document.body.removeChild(iframe); } catch (_) {} }, 2000);
      setDownloaded(true);
    } catch (err) {
      console.error('PDF generation failed:', err);
      try {
        const fullDoc = buildPdfDocument(reportHtml);
        const blob = new Blob([fullDoc], { type: 'text/html' });
        const url = URL.createObjectURL(blob);
        const win = window.open(url, '_blank');
        if (win) win.addEventListener('load', () => { win.print(); URL.revokeObjectURL(url); });
      } catch (_) {}
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className="max-w-[780px]">
      <div className="rounded-2xl border border-neutral-800 bg-[#0C0C0C] p-5">
        <div className="flex items-start gap-3 mb-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-red-500/10 shrink-0">
            <FileText size={18} className="text-red-400" />
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-[10px] font-bold uppercase tracking-[0.18em] text-red-400/70 mb-1">Report Generated</div>
            <div className="text-[15px] font-semibold text-white leading-tight truncate">{reportTitle}</div>
            <p className="mt-1.5 text-[12px] text-neutral-500 leading-relaxed">
              Click below to save as PDF. Select &quot;Save as PDF&quot; in the print dialog.
            </p>
          </div>
        </div>
        <button
          onClick={handleDownloadPdf}
          disabled={downloading}
          className={`w-full flex items-center justify-center gap-2.5 rounded-xl px-5 py-3 text-[14px] font-semibold transition-all ${
            downloaded
              ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
              : downloading
                ? 'bg-neutral-800 border border-neutral-700 text-neutral-400 cursor-wait'
                : 'bg-white text-black hover:bg-neutral-200 active:scale-[0.98]'
          }`}
        >
          {downloading ? (
            <><Loader2 size={16} className="animate-spin" /> Preparing PDF...</>
          ) : downloaded ? (
            <><CheckCircle2 size={16} /> Done — Click to save again</>
          ) : (
            <><Download size={16} /> Save Report as PDF</>
          )}
        </button>
      </div>
    </div>
  );
}
