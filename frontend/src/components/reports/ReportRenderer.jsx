import React, { useRef, useState } from 'react';
import { CheckCircle2, Download, FileText, Loader2 } from 'lucide-react';

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
    margin: 0 auto; padding: 0;
    max-width: 178mm;
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
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Frammer Report</title>
<style>${PDF_CSS}</style>
</head>
<body>
${PAGE_HEADER_HTML}
${reportHtml}
</body>
</html>`;
}

export default function ReportRenderer({ reportHtml }) {
  const [downloading, setDownloading] = useState(false);
  const [downloaded, setDownloaded] = useState(false);
  const [iframeHeight, setIframeHeight] = useState(600);
  const iframeRef = useRef(null);

  // postMessage listener for sandbox-safe auto-resize (must be before early return for hooks rules)
  React.useEffect(() => {
    const handler = (e) => {
      if (e.data?.type === 'report-iframe-resize' && typeof e.data.height === 'number') {
        setIframeHeight(Math.min(Math.max(e.data.height + 40, 400), 2000));
      }
    };
    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, []);

  if (!reportHtml) return null;

  const titleMatch = reportHtml.match(/<(?:h1)[^>]*>(.*?)<\/(?:h1)>/si)
    || reportHtml.match(/<div\s+class="report-title">(.*?)<\/div>/si);
  const reportTitle = titleMatch
    ? titleMatch[1].replace(/<[^>]+>/g, '').trim()
    : 'Analytical Report';

  // Build full document once — used for both preview and PDF export
  const trimmed = reportHtml.trim().toLowerCase();
  const isFullDocument = trimmed.startsWith('<!doctype html') || trimmed.startsWith('<html');
  const baseDoc = isFullDocument ? reportHtml : buildPdfDocument(reportHtml);

  // Inject a postMessage resize script so the sandboxed iframe (no allow-same-origin)
  // can communicate its content height to the parent for auto-resize.
  const resizeScript = `<script>
    function _notifyHeight() {
      var h = document.documentElement.scrollHeight || document.body.scrollHeight;
      window.parent.postMessage({ type: 'report-iframe-resize', height: h }, '*');
    }
    window.addEventListener('load', function() { setTimeout(_notifyHeight, 200); });
    new MutationObserver(_notifyHeight).observe(document.body, { childList: true, subtree: true });
  <\/script>`;
  const fullDoc = baseDoc.replace(/<\/body>/i, resizeScript + '</body>');

  const handleDownloadPdf = async () => {
    setDownloading(true);
    setDownloaded(false);
    try {
      const iframe = document.createElement('iframe');
      iframe.style.cssText = 'position:fixed;left:-9999px;top:0;width:900px;height:1200px;border:none;';
      document.body.appendChild(iframe);

      const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
      iframeDoc.open();
      iframeDoc.write(fullDoc);
      iframeDoc.close();

      await new Promise((resolve) => {
        if (iframe.contentWindow.document.readyState === 'complete') resolve();
        else iframe.contentWindow.addEventListener('load', resolve);
      });

      if (isFullDocument) {
        const start = Date.now();
        while (Date.now() - start < 5000) {
          const chartReady = iframe.contentWindow.Chart;
          const canvases = iframeDoc.querySelectorAll('canvas');
          if (chartReady && canvases.length === 0) break;
          if (chartReady && canvases.length > 0) {
            await new Promise((r) => setTimeout(r, 500));
            break;
          }
          await new Promise((r) => setTimeout(r, 200));
        }
      } else {
        await new Promise((r) => setTimeout(r, 300));
      }

      iframe.contentWindow.focus();
      iframe.contentWindow.print();

      setTimeout(() => { try { document.body.removeChild(iframe); } catch (_) {} }, 2000);
      setDownloaded(true);
    } catch (err) {
      console.error('PDF generation failed:', err);
      try {
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
      {/* Inline report preview */}
      <div className="rounded-2xl border border-neutral-800 bg-white overflow-hidden mb-4">
        <iframe
          ref={iframeRef}
          srcDoc={fullDoc}
          style={{ width: '100%', height: `${iframeHeight}px`, border: 'none' }}
          sandbox="allow-scripts"
          title={reportTitle}
        />
      </div>

      {/* Compact download bar */}
      <div className="flex items-center justify-between rounded-2xl border border-neutral-800 bg-[#0C0C0C] px-5 py-3">
        <div className="flex items-center gap-2.5 min-w-0">
          <FileText size={14} className="text-red-400 shrink-0" />
          <span className="text-[13px] font-semibold text-neutral-400 truncate">{reportTitle}</span>
        </div>
        <button
          onClick={handleDownloadPdf}
          disabled={downloading}
          className={`flex items-center gap-2 rounded-xl px-4 py-2 text-[13px] font-semibold transition-all shrink-0 ml-3 ${
            downloaded
              ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400'
              : downloading
                ? 'bg-neutral-800 border border-neutral-700 text-neutral-400 cursor-wait'
                : 'bg-white text-black hover:bg-neutral-200 active:scale-[0.98]'
          }`}
        >
          {downloading ? (
            <><Loader2 size={14} className="animate-spin" /> Preparing...</>
          ) : downloaded ? (
            <><CheckCircle2 size={14} /> Save again</>
          ) : (
            <><Download size={14} /> Save as PDF</>
          )}
        </button>
      </div>
    </div>
  );
}
