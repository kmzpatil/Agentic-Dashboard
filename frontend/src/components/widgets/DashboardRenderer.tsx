import React from "react";
import { parseXML } from "../../utils/parser";
import { T } from "../../utils/theme";
import { ErrW } from "../ui/SharedUI";
import type { WidgetProps } from "../../store/index";

// Import your extracted charts here
import { WKpi, WBar, WPie, WHeatmap, WRadarGrid, WLine } from "./ChartWidgets";

// ════════════════════════════════════════════════════════════════
//  WIDGET REGISTRY
// ════════════════════════════════════════════════════════════════
const REGISTRY: Record<string, React.FC<WidgetProps>> = {
  "kpi": WKpi,
  "bar-chart": WBar,
  "pie-chart": WPie,
  "heatmap": WHeatmap,
  "radar-grid": WRadarGrid,
  "line-chart": WLine,
};

// ════════════════════════════════════════════════════════════════
//  DASHBOARD RENDERER
// ════════════════════════════════════════════════════════════════
export default function DashboardRenderer({ xml }: { xml: string }) {
  const cfg = parseXML(xml);
  
  if (cfg.error) return (
    <div style={{ background: "#1a0505", border: `1px solid ${T.danger}`, borderRadius: 8, padding: 24, fontSize: 13, color: T.danger }}>
      <strong>XML Error</strong><br />{cfg.error}
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {cfg.rows?.map(row => (
        <div key={row.id}>
          {row.label && (
            <div style={{ fontSize: 16, fontWeight: 600, color: T.text, marginBottom: 16, borderBottom: `1px solid ${T.border}`, paddingBottom: 8 }}>{row.label}</div>
          )}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(12,1fr)", gap: 16 }}>
            {row.widgets.map((w, index) => {
              const Comp = REGISTRY[w.type];
              const col = parseInt(w.col) || 1;
              const span = parseInt(w.span) || 4;
              return (
                <div key={w.id || index} style={{ gridColumn: `${col} / span ${span}` }}>
                  {Comp ? <Comp a={w} /> : <ErrW msg={`Unknown widget type: "${w.type}"`} />}
                </div>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}