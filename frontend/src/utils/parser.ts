import type { ParsedXML } from "../store";

// ════════════════════════════════════════════════════════════════
//  XML PARSER
// ════════════════════════════════════════════════════════════════

export function parseXML(xmlStr: string): ParsedXML {
  try {
    const doc = new DOMParser().parseFromString(xmlStr, "application/xml");
    const err = doc.querySelector("parsererror");
    if (err) return { error: "XML parse error: " + err.textContent?.slice(0, 120) };

    const meta = {
      title: doc.querySelector("meta > title")?.textContent || "Dashboard",
      description: doc.querySelector("meta > description")?.textContent || "",
    };

    const rows: ParsedXML['rows'] = [];
    doc.querySelectorAll("layout > row").forEach(rowEl => {
      const widgets: Record<string, string>[] = [];
      rowEl.querySelectorAll("widget").forEach(w => {
        const a: Record<string, string> = {};
        for (let i = 0; i < w.attributes.length; i++) {
          const attr = w.attributes[i];
          a[attr.name] = attr.value;
        }
        widgets.push(a);
      });
      rows.push({ id: rowEl.getAttribute("id"), label: rowEl.getAttribute("label") || "", widgets });
    });

    const noticeEl = doc.querySelector("notice");
    const notice = noticeEl ? noticeEl.getAttribute("message") : null;
    return { meta, rows, notice };
  } catch (e) {
    return { error: String(e) };
  }
}

// ════════════════════════════════════════════════════════════════
//  DATA STORE BUILDER
// ════════════════════════════════════════════════════════════════

export function buildDataStoreFromResponse(xmlStr: string, chartData: Record<string, any>): Record<string, any> {
  try {
    const doc = new DOMParser().parseFromString(xmlStr, "application/xml");
    const store: Record<string, any> = {};

    doc.querySelectorAll("layout > row > widget").forEach(widgetEl => {
      const source = widgetEl.getAttribute("data-source");
      const title = widgetEl.getAttribute("title");
      if (!source || !title || store[source]) return;

      const records = chartData?.[title];
      if (!Array.isArray(records) || records.length === 0) return;

      const type = widgetEl.getAttribute("type");
      if (type === "kpi") {
        store[source] = records[0] || {};
      } else {
        store[source] = records;
      }
    });

    return store;
  } catch {
    return {};
  }
}