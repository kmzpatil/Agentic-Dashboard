/**
 * reportXmlParser.js
 * ──────────────────
 * Parses a <report> XML string into a structured JS object
 * compatible with ReportRenderer.
 */

function getTextContent(parent, tagName) {
  const el = parent?.querySelector(tagName);
  return el?.textContent?.trim() || '';
}

function parseChartConfig(sectionEl) {
  const chartEl = sectionEl.querySelector('chart_config');
  if (!chartEl) return null;
  return {
    chartType: getTextContent(chartEl, 'chart_type') || 'bar',
    title: getTextContent(chartEl, 'title'),
    xColumn: getTextContent(chartEl, 'x_column'),
    yColumns: getTextContent(chartEl, 'y_columns'),
  };
}

function parseDataTable(sectionEl) {
  const tableEl = sectionEl.querySelector('data_table');
  if (!tableEl) return null;

  const columns = Array.from(tableEl.querySelectorAll('columns > col')).map(col => ({
    name: col.getAttribute('name') || '',
    field: col.getAttribute('field') || '',
    format: col.getAttribute('format') || 'text',
  }));

  const rows = Array.from(tableEl.querySelectorAll('rows > row')).map(row => {
    const obj = {};
    for (const col of columns) {
      obj[col.field] = row.getAttribute(col.field) || '';
    }
    return obj;
  });

  return { columns, rows };
}

function parseKeyFindings(sectionEl) {
  return Array.from(sectionEl.querySelectorAll('key_findings > finding')).map(f => ({
    severity: f.getAttribute('severity') || 'info',
    text: f.textContent?.trim() || '',
  }));
}

function parseSections(doc) {
  return Array.from(doc.querySelectorAll('sections > section')).map(sec => ({
    type: sec.getAttribute('type') || 'breakdown',
    heading: getTextContent(sec, 'heading'),
    narrative: getTextContent(sec, 'narrative'),
    chart: parseChartConfig(sec),
    dataTable: parseDataTable(sec),
    keyFindings: parseKeyFindings(sec),
  }));
}

/**
 * Parse a report XML string into a structured object.
 * Returns null if the XML is invalid or doesn't contain a <report> root.
 *
 * @param {string} xmlString
 * @returns {object|null}
 */
export function parseReportXml(xmlString) {
  if (!xmlString || typeof xmlString !== 'string') return null;

  try {
    const parser = new DOMParser();
    const doc = parser.parseFromString(xmlString, 'text/xml');

    // Check for parse errors
    const parseError = doc.querySelector('parsererror');
    if (parseError) return null;

    const report = doc.querySelector('report');
    if (!report) return null;

    // Metadata
    const metadata = {
      title: getTextContent(report, 'metadata > title'),
      subtitle: getTextContent(report, 'metadata > subtitle'),
      dateRange: getTextContent(report, 'metadata > date_range'),
      originalQuery: getTextContent(report, 'metadata > original_query'),
      generatedAt: getTextContent(report, 'metadata > generated_at'),
    };

    // Executive summary
    const executiveSummary = getTextContent(report, 'executive_summary');

    // Sections
    const sections = parseSections(report);

    // Conclusions
    const conclusions = Array.from(report.querySelectorAll('conclusions > conclusion'))
      .map(c => c.textContent?.trim() || '');

    // Recommendations
    const recommendations = Array.from(report.querySelectorAll('recommendations > recommendation'))
      .map(r => ({
        priority: parseInt(r.getAttribute('priority') || '0', 10),
        text: r.textContent?.trim() || '',
      }))
      .sort((a, b) => a.priority - b.priority);

    return {
      metadata,
      executiveSummary,
      sections,
      conclusions,
      recommendations,
    };
  } catch {
    return null;
  }
}

/**
 * Check if a string looks like report XML.
 */
export function isReportXml(text) {
  if (!text || typeof text !== 'string') return false;
  const trimmed = text.trim();
  return (trimmed.startsWith('<?xml') || trimmed.startsWith('<report')) && trimmed.includes('</report>');
}
