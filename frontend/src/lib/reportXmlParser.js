/**
 * reportParser.js
 * ────────────────
 * Utilities for detecting and cleaning report HTML from the agent.
 */

/**
 * Check if a string looks like report HTML.
 * Detects both full self-contained documents (from render_report_html)
 * and legacy fragment format (<div class="report">).
 */
export function isReportHtml(text) {
  if (!text || typeof text !== 'string' || text.length < 30) return false;
  const t = text.trim().toLowerCase();
  // Full self-contained HTML document (from report_formatter.py)
  if (t.startsWith('<!doctype html') || t.startsWith('<html')) return true;
  // Legacy fragment format: <div class="report">
  return (
    (t.includes('class="report"') || t.includes("class='report'") || t.includes('class=report')) &&
    t.includes('</div>')
  );
}

/**
 * Strip markdown code fences and extract the report HTML.
 * Passes through full self-contained documents unchanged.
 */
export function cleanReportHtml(html) {
  if (!html) return '';
  let cleaned = html.trim();
  // Strip ```html ... ``` wrapping
  cleaned = cleaned.replace(/^```(?:html)?\s*\n?/i, '');
  cleaned = cleaned.replace(/\n?```\s*$/, '');
  cleaned = cleaned.trim();

  // If it's a complete document, return as-is (don't strip head/style/script tags)
  const lower = cleaned.toLowerCase();
  if (lower.startsWith('<!doctype html') || lower.startsWith('<html')) {
    return cleaned;
  }

  // Legacy fragment: extract from <div class="report">
  const startIdx = cleaned.search(/<div\s[^>]*class\s*=\s*["']?report["']?/i);
  if (startIdx > 0) {
    cleaned = cleaned.substring(startIdx);
  }

  return cleaned;
}

// Legacy compat
export const isReportXml = isReportHtml;
export const parseReportXml = (html) => (isReportHtml(html) ? cleanReportHtml(html) : null);
