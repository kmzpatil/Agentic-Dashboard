import React from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, LineChart, Line,
} from "recharts";
import { type WidgetProps, DATA_STORE } from "../../store";
import { T, MULTI, scheme } from "../../utils/theme";
import { Card, WHead, RTip, ErrW } from "../ui/SharedUI";

export function WKpi({ a }: WidgetProps) {
  const src = DATA_STORE[a["data-source"]];
  if (!src) return <ErrW msg={`Unknown data-source: ${a["data-source"]}`} />;

  let val = src[a.metric];
  if (a.unit === "hours") val = `${Math.round(val / 3600).toLocaleString()}h`;
  else val = typeof val === "number" ? val.toLocaleString() : "—";

  return (
    <Card style={{ display: "flex", flexDirection: "column", justifyContent: "center", borderTop: `3px solid ${scheme(a["color-scheme"] || "red")}` }}>
      <div style={{ fontSize: 12, color: T.muted, fontWeight: 500, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>{a.title}</div>
      <div style={{ fontSize: 32, fontWeight: 700, color: T.text, letterSpacing: "-0.02em", lineHeight: 1 }}>{val}</div>
    </Card>
  );
}

export function WBar({ a }: WidgetProps) {
  const src = DATA_STORE[a["data-source"]];
  if (!src) return <ErrW msg={`Unknown data-source: ${a["data-source"]}`} />;

  const yFields = a["y-fields"].split(",");
  const yLabels = a["y-labels"] ? a["y-labels"].split(",") : yFields;
  const showLeg = a["show-legend"] === "true";

  return (
    <Card>
      <WHead title={a.title} />
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={src} margin={{ top: 0, right: 0, left: -20, bottom: a["x-label"] ? 14 : 0 }} barCategoryGap="30%">
          <CartesianGrid strokeDasharray="3 3" stroke={T.border} vertical={false} opacity={0.6} />
          <XAxis dataKey={a["x-field"]} tick={{ fontSize: 11, fill: T.muted }} tickLine={false} axisLine={{ stroke: T.border }}
            tickFormatter={(v: any) => a["x-tick-short"] === "true" ? String(v).split(" ")[0] : v}
            label={a["x-label"] ? { value: a["x-label"], position: "insideBottom", offset: -6, fontSize: 11, fill: T.faint } : undefined} />
          <YAxis tick={{ fontSize: 11, fill: T.muted }} tickLine={false} axisLine={{ stroke: T.border }} />
          <Tooltip content={<RTip />} cursor={{ fill: '#1a1a1a' }} />
          {showLeg && <Legend iconType="circle" iconSize={6} wrapperStyle={{ fontSize: 11, paddingTop: 12, color: T.muted }} />}
          {yFields.map((f, i) => (
            <Bar key={f} dataKey={f} name={yLabels[i] || f} fill={scheme(a["color-scheme"] || "multi", i)} radius={[2, 2, 0, 0]} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </Card>
  );
}

export function WPie({ a }: WidgetProps) {
  const src = DATA_STORE[a["data-source"]];
  if (!src) return <ErrW msg={`Unknown data-source: ${a["data-source"]}`} />;

  const nF = a["name-field"], vF = a["value-field"];
  const donut = a.variant === "donut";

  return (
    <Card>
      <WHead title={a.title} />
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <ResponsiveContainer width={160} height={160}>
          <PieChart>
            <Pie data={src} dataKey={vF} nameKey={nF} cx="50%" cy="50%"
              innerRadius={donut ? 55 : 0} outerRadius={75} paddingAngle={donut ? 2 : 0} stroke="none">
              {src.map((_: any, i: number) => <Cell key={i} fill={MULTI[i % MULTI.length]} />)}
            </Pie>
            <Tooltip content={<RTip />} />
          </PieChart>
        </ResponsiveContainer>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
          {src.map((row: any, i: number) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <div style={{ width: 8, height: 8, borderRadius: "50%", background: MULTI[i % MULTI.length], flexShrink: 0 }} />
              <span style={{ fontSize: 12, color: T.muted, flex: 1 }}>{row[nF]}</span>
              <span style={{ fontSize: 12, fontWeight: 600, color: T.text }}>{Number(row[vF]).toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

export function WHeatmap({ a }: WidgetProps) {
  const src = DATA_STORE[a["data-source"]];
  if (!src) return <ErrW msg={`Unknown data-source: ${a["data-source"]}`} />;

  const cols = a["col-fields"].split(",");
  const labels = a["col-labels"] ? a["col-labels"].split(",") : cols;
  const rowF = a["row-field"];
  const maxV = Math.max(...src.flatMap((r: any) => cols.map((c: string) => Number(r[c]) || 0)));

  const heat = (v: number) => {
    const t = v / maxV;
    if (t < 0.15) return { bg: "#111111", fg: T.faint };
    if (t < 0.35) return { bg: "#450a0a", fg: "#fca5a5" };
    if (t < 0.6) return { bg: "#7f1d1d", fg: "#ffffff" };
    if (t < 0.8) return { bg: "#b91c1c", fg: "#ffffff" };
    return { bg: "#e00000", fg: "#ffffff" };
  };

  return (
    <Card>
      <WHead title={a.title} />
      <div style={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "separate", borderSpacing: "3px", fontSize: 12 }}>
          <thead>
            <tr>
              <th style={{ textAlign: "left", padding: "8px 12px", color: T.muted, fontWeight: 500, minWidth: 100 }}>Channel</th>
              {labels.map((l: string, i: number) => (
                <th key={i} style={{ textAlign: "center", padding: "4px", color: T.muted, fontWeight: 500, minWidth: 64, fontSize: 11, lineHeight: 1.3 }}>
                  {l.split(" ").map((w, j) => <div key={j}>{w}</div>)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {src.map((row: any, ri: number) => (
              <tr key={ri}>
                <td style={{ padding: "10px 12px", color: T.text, fontWeight: 500 }}>{row[rowF]}</td>
                {cols.map((c: string, ci: number) => {
                  const v = Number(row[c]) || 0;
                  const { bg, fg } = heat(v);
                  return (
                    <td key={ci} style={{ textAlign: "center", padding: "10px 4px", background: bg, color: fg, borderRadius: 4, fontWeight: v / maxV > 0.6 ? 600 : 400 }}>{v}</td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 16, justifyContent: "flex-end" }}>
          <span style={{ fontSize: 11, color: T.faint }}>Low</span>
          {["#111111", "#450a0a", "#7f1d1d", "#b91c1c", "#e00000"].map((c, i) => (
            <div key={i} style={{ width: 20, height: 6, background: c, borderRadius: 2 }} />
          ))}
          <span style={{ fontSize: 11, color: T.faint }}>High</span>
        </div>
      </div>
    </Card>
  );
}

export function WRadarGrid({ a }: WidgetProps) {
  const src = DATA_STORE[a["data-source"]];
  if (!src) return <ErrW msg={`Unknown data-source: ${a["data-source"]}`} />;

  const fields = a.fields.split(",");
  const labels = a["field-labels"] ? a["field-labels"].split(",") : fields;
  const gF = a["group-field"];

  return (
    <Card>
      <WHead title={a.title} />
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 20 }}>
        {src.map((row: any, ri: number) => {
          const data = fields.map((f: string, fi: number) => ({ s: labels[fi], v: row[f] || 0 }));
          return (
            <div key={ri} style={{ textAlign: "center" }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: T.text, marginBottom: 4 }}>{row[gF]}</div>
              <ResponsiveContainer width="100%" height={140}>
                <RadarChart data={data} margin={{ top: 8, right: 16, bottom: 8, left: 16 }}>
                  <PolarGrid stroke={T.border} />
                  <PolarAngleAxis dataKey="s" tick={{ fontSize: 10, fill: T.muted }} />
                  <Radar dataKey="v" stroke={T.accent} fill={T.accent} fillOpacity={0.2} strokeWidth={1.5} />
                </RadarChart>
              </ResponsiveContainer>
            </div>
          );
        })}
      </div>
    </Card>
  );
}

export function WLine({ a }: WidgetProps) {
  const src = DATA_STORE[a["data-source"]];
  if (!src) return <ErrW msg={`Unknown data-source: ${a["data-source"]}`} />;

  const yF = a["y-fields"].split(",");
  const yL = a["y-labels"] ? a["y-labels"].split(",") : yF;

  return (
    <Card>
      <WHead title={a.title} />
      <ResponsiveContainer width="100%" height={200}>
        <LineChart data={src} margin={{ top: 0, right: 0, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={T.border} vertical={false} opacity={0.6} />
          <XAxis dataKey={a["x-field"]} tick={{ fontSize: 11, fill: T.muted }} tickLine={false} axisLine={{ stroke: T.border }} />
          <YAxis tick={{ fontSize: 11, fill: T.muted }} tickLine={false} axisLine={{ stroke: T.border }} />
          <Tooltip content={<RTip />} />
          <Legend iconType="circle" iconSize={6} wrapperStyle={{ fontSize: 11, paddingTop: 12, color: T.muted }} />
          {yF.map((f, i) => (
            <Line key={f} type="monotone" dataKey={f} name={yL[i] || f}
              stroke={scheme(a["color-scheme"] || "multi", i)} strokeWidth={2} dot={{ fill: T.surface, r: 3, strokeWidth: 2 }} activeDot={{ r: 5, strokeWidth: 0, fill: T.text }} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}