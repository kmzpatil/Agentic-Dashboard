/**
 * reportParser.js
 * ────────────────
 * Utilities for detecting and cleaning report HTML from the agent.
 */

/**
 * Check if a string looks like report HTML.
 * Lenient detection — handles single/double quotes, extra whitespace, etc.
 */
export function isReportHtml(text) {
  if (!text || typeof text !== 'string' || text.length < 30) return false;
  const t = text.trim().toLowerCase();
  // Check for any variation of <div class="report"> or class='report'
  return (
    (t.includes('class="report"') || t.includes("class='report'") || t.includes('class=report')) &&
    t.includes('</div>')
  );
}

/**
 * Strip markdown code fences and extract the report HTML.
 */
export function cleanReportHtml(html) {
  if (!html) return '';
  let cleaned = html.trim();
  // Strip ```html ... ``` wrapping
  cleaned = cleaned.replace(/^```(?:html)?\s*\n?/i, '');
  cleaned = cleaned.replace(/\n?```\s*$/, '');
  cleaned = cleaned.trim();

  // If the content has <div class="report"> somewhere inside, extract from there
  const startIdx = cleaned.search(/<div\s[^>]*class\s*=\s*["']?report["']?/i);
  if (startIdx > 0) {
    cleaned = cleaned.substring(startIdx);
  }

  return cleaned;
}

// Legacy compat
export const isReportXml = isReportHtml;
export const parseReportXml = (html) => (isReportHtml(html) ? cleanReportHtml(html) : null);
