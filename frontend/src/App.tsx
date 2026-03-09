import React, { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, LineChart, Line,
} from "recharts";
// import VideoExplorerTable from "./components/VideoExplorerTable";

// ════════════════════════════════════════════════════════════════
//  TYPES & INTERFACES
// ════════════════════════════════════════════════════════════════

interface ChatMessage {
  role: "user" | "agent";
  text: string;
  xml?: string;
  isErr?: boolean;
}

interface ParsedXML {
  meta?: { title: string; description: string };
  rows?: Array<{
    id: string | null;
    label: string;
    widgets: Record<string, string>[];
  }>;
  notice?: string | null;
  error?: string;
}

interface WidgetProps {
  a: Record<string, string>;
}

interface CardProps {
  children: React.ReactNode;
  style?: React.CSSProperties;
}

// ════════════════════════════════════════════════════════════════
//  DATA STORE
// ════════════════════════════════════════════════════════════════
let DATA_STORE: Record<string, any> = {};

// ════════════════════════════════════════════════════════════════
//  MASTER XML
// ════════════════════════════════════════════════════════════════
const MASTER_XML: string = `<dashboard version="1.0" theme="dark" cols="12">
  <meta>
    <title>Live Media Analytics</title>
    <description>Use Agent Chat to generate charts from backend data</description>
    <created>2026-03-09</created>
    <notice message="No sample CSV is loaded. Run a query to populate dashboard data." />
  </meta>
  <layout></layout>
</dashboard>`;

// ════════════════════════════════════════════════════════════════
//  RED/WHITE/BLACK DESIGN TOKENS
// ════════════════════════════════════════════════════════════════
const T = {
  bg: "#050505",       // Deep black background
  surface: "#111111",  // Slightly lighter black for panels/cards
  border: "#262626",   // Dark gray borders
  text: "#ffffff",     // Pure white text
  muted: "#a3a3a3",    // Gray text for secondary info
  faint: "#525252",    // Darker gray for inactive elements
  accent: "#e00000",   // Bold red
  danger: "#ef4444",   // Lighter red for errors
};

// Red, White, and Grayscale Palette
const PALETTE: Record<string, string> = { red: "#e00000", white: "#ffffff", gray: "#737373", darkgray: "#404040" };
const MULTI: string[] = ["#e00000", "#ffffff", "#a3a3a3", "#525252", "#991b1b"];
const scheme = (s: string, i: number = 0): string => s === "multi" ? MULTI[i % MULTI.length] : (PALETTE[s] || T.accent);

// ════════════════════════════════════════════════════════════════
//  XML PARSER
// ════════════════════════════════════════════════════════════════
function parseXML(xmlStr: string): ParsedXML {
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

function buildDataStoreFromResponse(xmlStr: string, chartData: Record<string, any>): Record<string, any> {
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

// ════════════════════════════════════════════════════════════════
//  SHARED PRIMITIVES
// ════════════════════════════════════════════════════════════════
function Card({ children, style = {} }: CardProps) {
  return <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 8, padding: "20px", height: "100%", ...style }}>{children}</div>;
}

function WHead({ title }: { title: string }) {
  return <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.05em" }}>{title}</div>;
}

const RTip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: "#000", border: `1px solid ${T.accent}`, borderRadius: 4, padding: "8px 12px", fontSize: 12, boxShadow: "0 4px 12px rgba(224,0,0,0.15)" }}>
      {label && <div style={{ fontWeight: 600, color: T.text, marginBottom: 6 }}>{label}</div>}
      {payload.map((p: any, i: number) => (
        <div key={i} style={{ color: p.color, display: "flex", gap: 12 }}>
          <span>{p.name}:</span><span style={{ fontWeight: 600 }}>{typeof p.value === "number" ? p.value.toLocaleString() : p.value}</span>
        </div>
      ))}
    </div>
  );
};

// ════════════════════════════════════════════════════════════════
//  WIDGET COMPONENTS
// ════════════════════════════════════════════════════════════════
function ErrW({ msg }: { msg: string }) {
  return (
    <div style={{ background: "#1a0505", border: `1px solid ${T.danger}`, borderRadius: 8, padding: "20px", height: "100%", display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ color: T.danger }}>⚠</span>
      <span style={{ fontSize: 12, color: T.danger }}>{msg}</span>
    </div>
  );
}

function WKpi({ a }: WidgetProps) {
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

function WBar({ a }: WidgetProps) {
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

function WPie({ a }: WidgetProps) {
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

function WHeatmap({ a }: WidgetProps) {
  const src = DATA_STORE[a["data-source"]];
  if (!src) return <ErrW msg={`Unknown data-source: ${a["data-source"]}`} />;

  const cols = a["col-fields"].split(",");
  const labels = a["col-labels"] ? a["col-labels"].split(",") : cols;
  const rowF = a["row-field"];
  const maxV = Math.max(...src.flatMap((r: any) => cols.map((c: string) => Number(r[c]) || 0)));

  // Black -> Dark Red -> Bright Red heatmap
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
              {labels.map((l, i) => (
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

function WRadarGrid({ a }: WidgetProps) {
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

function WLine({ a }: WidgetProps) {
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
function DashboardRenderer({ xml }: { xml: string }) {
  const cfg = parseXML(xml);
  if (cfg.error) return (
    <div style={{ background: "#1a0505", border: `1px solid ${T.danger}`, borderRadius: 8, padding: 24, fontSize: 13, color: T.danger }}>
      <strong>XML Error</strong><br />{cfg.error}
    </div>
  );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      {/* Header logic moved outside, but rows remain */}
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

// ════════════════════════════════════════════════════════════════
//  XML SYNTAX VIEWER
// ════════════════════════════════════════════════════════════════
function XMLViewer({ xml }: { xml: string }) {
  return (
    <div style={{ fontFamily: "'JetBrains Mono','Fira Code',monospace", fontSize: 11, lineHeight: 1.9, overflowX: "auto" }}>
      {xml.trim().split("\n").map((raw, i) => {
        const esc = raw.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        const hi = esc
          .replace(/(&lt;\/?)([\w-]+)/g, (_, p, t) => `${p}<span style="color:#ef4444;font-weight:600">${t}</span>`)
          .replace(/([\w-]+)=&quot;([^&]*)&quot;/g, (_, a, v) => `<span style="color:#a3a3a3">${a}</span>=<span style="color:#ffffff">"${v}"</span>`)
          .replace(/&lt;!--([\s\S]*?)--&gt;/g, (_, c) => `<span style="color:#525252">&lt;!--${c}--&gt;</span>`);
        return (
          <div key={i} style={{ display: "flex" }}>
            <span style={{ color: T.faint, userSelect: "none", marginRight: 14, minWidth: 26, textAlign: "right", flexShrink: 0 }}>{i + 1}</span>
            <span dangerouslySetInnerHTML={{ __html: hi }} />
          </div>
        );
      })}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
//  APP SHELL & INTERACTIVE DASHBOARD
// ════════════════════════════════════════════════════════════════
export default function App() {
  const navigate = useNavigate();
  const [mode, setMode] = useState<"static" | "interactive">("interactive");
  const [xml, setXml] = useState<string>(MASTER_XML);
  const [history, setHistory] = useState<string[]>([MASTER_XML]);
  const [msgs, setMsgs] = useState<ChatMessage[]>([
    { role: "agent", text: "SYSTEM ONLINE. I can modify dashboard configurations via XML. Select a prompt below or type instructions." }
  ]);
  const [input, setInput] = useState<string>("");
  const [status, setStatus] = useState<"idle" | "thinking" | "error">("idle");
  const [rightTab, setRightTab] = useState<string>("chat");
  const [notice, setNotice] = useState<string | null>(null);

  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  const cfg = parseXML(xml);
  const wCount = cfg.rows?.reduce((s, r) => s + r.widgets.length, 0) || 0;

  async function send() {
    const msg = input.trim();
    if (!msg || status === "thinking") return;
    setInput("");
    setMsgs(p => [...p, { role: "user", text: msg }]);
    setStatus("thinking");
    setNotice(null);

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: msg }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => null);
        const detail = errData?.detail || `Request failed with status ${res.status}`;
        setMsgs(p => [...p, { role: "agent", text: `Error: ${detail}`, isErr: true }]);
        setStatus("error");
        return;
      }

      const data = await res.json();
      if (data.error) {
        setMsgs(p => [...p, { role: "agent", text: `Error: ${data.error}`, isErr: true }]);
        setStatus("error");
        return;
      }

      const rawXml = typeof data.xml === "string" ? data.xml : "";
      const match = rawXml.match(/<dashboard[\s\S]*<\/dashboard>/);

      if (!match) {
        setMsgs(p => [...p, { role: "agent", text: "No valid dashboard XML returned from backend.", isErr: true }]);
        setStatus("error"); return;
      }

      const newXml = match[0];
      const parsed = parseXML(newXml);

      if (parsed.error) {
        setMsgs(p => [...p, { role: "agent", text: `Validation failed: ${parsed.error}`, isErr: true }]);
        setStatus("error"); return;
      }

      if (parsed.notice) {
        setNotice(parsed.notice);
        setMsgs(p => [...p, { role: "agent", text: `⚠ ${parsed.notice}` }]);
        setStatus("idle"); return;
      }

      DATA_STORE = buildDataStoreFromResponse(newXml, data.chart_data || {});

      setHistory(h => [...h, newXml]);
      setXml(newXml);

      const nw = parsed.rows?.reduce((s, r) => s + r.widgets.length, 0) || 0;
      const diff = nw - wCount;
      const ds = diff > 0 ? ` (+${diff} widget${diff > 1 ? "s" : ""})`
        : diff < 0 ? ` (${diff} widget${Math.abs(diff) > 1 ? "s" : ""})` : "";

      const insightText = data.insights ? ` Insights: ${data.insights}` : "";
      setMsgs(p => [...p, { role: "agent", text: `Configuration updated${ds}. Layout verified.${insightText}`, xml: newXml }]);
      setStatus("idle");
    } catch (e) {
      const errorMsg = e instanceof Error ? e.message : String(e);
      setMsgs(p => [...p, { role: "agent", text: `Error: ${errorMsg}`, isErr: true }]);
      setStatus("error");
    }
  }

  function undo() {
    if (history.length <= 1) return;
    const prev = history[history.length - 2];
    setHistory(h => h.slice(0, -1));
    setXml(prev);
    setMsgs(p => [...p, { role: "agent", text: "Previous configuration restored." }]);
  }

  const SUGG: string[] = [
    "Build an executive dashboard with 4 key KPIs",
    "Show top 10 channels by published duration",
    "Compare user distribution by role as a donut chart",
  ];

  return (
    <div style={{ display: "flex", height: "100vh", background: T.bg, color: T.text, fontFamily: "'Inter', 'Segoe UI', sans-serif", overflow: "hidden" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:6px;height:6px}
        ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:#333;border-radius:3px}
        ::-webkit-scrollbar-thumb:hover{background:#525252}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
      `}</style>

      {/* ── LEFT SIDEBAR ── */}
      <div style={{ width: 360, background: T.surface, borderRight: `1px solid ${T.border}`, display: "flex", flexDirection: "column", flexShrink: 0, zIndex: 10 }}>

        {/* Branding & Header */}
        <div style={{ padding: "24px", borderBottom: `1px solid ${T.border}` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 20 }}>
            <div style={{ width: 32, height: 32, background: T.accent, borderRadius: 4, display: "flex", alignItems: "center", justifyContent: "center" }}>
              <span style={{ color: "#fff", fontSize: 14, fontWeight: 700, letterSpacing: "-1px" }}>PS</span>
            </div>
            <div>
              <div style={{ fontSize: 15, fontWeight: 700, color: T.text, letterSpacing: "0.02em" }}>PS FOR DATA</div>
              <div style={{ fontSize: 11, color: T.muted, textTransform: "uppercase", letterSpacing: "0.05em" }}>Media Analytics</div>
            </div>
          </div>

          {/* Mode Switcher */}
          <div style={{ display: "flex", background: T.bg, borderRadius: 6, padding: 4, border: `1px solid ${T.border}` }}>
            <button onClick={() => setMode("static")} style={{ flex: 1, padding: "6px", fontSize: 11, fontWeight: 600, border: "none", borderRadius: 4, cursor: "pointer", background: mode === "static" ? T.surface : "transparent", color: mode === "static" ? T.text : T.muted }}>STATIC</button>
            <button onClick={() => setMode("interactive")} style={{ flex: 1, padding: "6px", fontSize: 11, fontWeight: 600, border: "none", borderRadius: 4, cursor: "pointer", background: mode === "interactive" ? T.accent : "transparent", color: mode === "interactive" ? "#fff" : T.muted }}>INTERACTIVE</button>
          </div>
        </div>

        {/* Sidebar Content (Only visible in Interactive Mode) */}
        {mode === "interactive" ? (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
            {/* Tabs */}
            <div style={{ display: "flex", borderBottom: `1px solid ${T.border}`, flexShrink: 0 }}>
              {[["chat", "AGENT CHAT"], ["xml", "SOURCE XML"]].map(([k, lbl]) => (
                <button key={k} onClick={() => setRightTab(k)} style={{
                  flex: 1, padding: "12px 0", border: "none", cursor: "pointer", background: "transparent",
                  borderBottom: rightTab === k ? `2px solid ${T.accent}` : `2px solid transparent`,
                  color: rightTab === k ? T.text : T.faint, fontSize: 11, fontWeight: 600, letterSpacing: "0.05em"
                }}>{lbl}</button>
              ))}
            </div>

            {rightTab === "chat" ? (
              <>
                {/* Suggestions */}
                <div style={{ padding: "12px", borderBottom: `1px solid ${T.border}`, display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {SUGG.map(s => (
                    <button key={s} onClick={() => { setInput(s); inputRef.current?.focus(); }} style={{
                      fontSize: 10, padding: "6px 10px", background: T.bg, color: T.muted, border: `1px solid ${T.border}`, borderRadius: 4, cursor: "pointer"
                    }}>{s}</button>
                  ))}
                </div>

                {/* Chat Log */}
                <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
                  {msgs.map((m, i) => (
                    <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: m.role === "user" ? "flex-end" : "flex-start" }}>
                      <div style={{ fontSize: 10, fontWeight: 600, color: T.faint, marginBottom: 4, textTransform: "uppercase" }}>{m.role === "user" ? "User" : "System"}</div>
                      <div style={{
                        maxWidth: "90%", padding: "12px 14px", borderRadius: 6, fontSize: 13, lineHeight: 1.5,
                        background: m.role === "user" ? T.border : m.isErr ? "#450a0a" : T.bg,
                        color: m.isErr ? T.danger : T.text, border: m.isErr ? `1px solid ${T.danger}` : `1px solid ${m.role === "user" ? "transparent" : T.border}`
                      }}>{m.text}</div>
                    </div>
                  ))}
                  {status === "thinking" && (
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
                      <div style={{ fontSize: 10, fontWeight: 600, color: T.faint, marginBottom: 4 }}>SYSTEM</div>
                      <div style={{ padding: "12px 16px", background: T.bg, borderRadius: 6, border: `1px solid ${T.border}`, color: T.accent, fontSize: 12, fontWeight: 600, animation: "pulse 1.5s infinite" }}>
                        Processing Request...
                      </div>
                    </div>
                  )}
                  <div ref={endRef} />
                </div>

                {/* Input Area */}
                <div style={{ padding: "16px", borderTop: `1px solid ${T.border}`, background: T.bg }}>
                  <div style={{ display: "flex", gap: 8 }}>
                    <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)}
                      onKeyDown={e => e.key === "Enter" && send()}
                      placeholder="Enter command..."
                      style={{ flex: 1, padding: "10px 14px", borderRadius: 4, border: `1px solid ${T.border}`, fontSize: 13, color: T.text, outline: "none", background: T.surface, fontFamily: "inherit" }} />
                    <button onClick={send} disabled={status === "thinking"} style={{
                      padding: "0 16px", borderRadius: 4, border: "none", background: status === "thinking" ? T.border : T.accent, color: "#fff", fontSize: 12, fontWeight: 600, cursor: status === "thinking" ? "not-allowed" : "pointer", textTransform: "uppercase"
                    }}>Run</button>
                  </div>
                </div>
              </>
            ) : (
              /* XML Tab */
              <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
                <div style={{ padding: "12px 16px", borderBottom: `1px solid ${T.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <span style={{ fontSize: 11, color: T.muted }}>dashboard.xml</span>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={undo} disabled={history.length <= 1} style={{ fontSize: 10, padding: "4px 8px", background: T.bg, border: `1px solid ${T.border}`, color: T.muted, cursor: "pointer", borderRadius: 4 }}>UNDO</button>
                    <button onClick={() => navigator.clipboard?.writeText(xml)} style={{ fontSize: 10, padding: "4px 8px", background: T.bg, border: `1px solid ${T.border}`, color: T.text, cursor: "pointer", borderRadius: 4 }}>COPY</button>
                  </div>
                </div>
                <div style={{ flex: 1, overflowY: "auto", padding: "16px", background: "#0a0a0a" }}>
                  <XMLViewer xml={xml} />
                </div>
              </div>
            )}
          </div>
        ) : (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 32, textAlign: "center" }}>
            <div style={{ width: 48, height: 48, borderRadius: "50%", background: T.bg, border: `1px solid ${T.border}`, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
              <span style={{ fontSize: 20, color: T.faint }}>⊞</span>
            </div>
            <div style={{ fontSize: 14, fontWeight: 600, color: T.text, marginBottom: 8 }}>Static Mode Active</div>
            <div style={{ fontSize: 12, color: T.muted, lineHeight: 1.5 }}>The dashboard is currently locked for viewing. Switch to Interactive mode to modify the layout using the Agent.</div>
          </div>
        )}
      </div>

      {/* ── MAIN DASHBOARD CANVAS ── */}
      <div style={{ flex: 1, overflowY: "auto", background: T.bg, position: "relative" }}>
        {notice && (
          <div style={{ position: "sticky", top: 0, zIndex: 100, padding: "12px 24px", background: T.danger, color: "#fff", fontSize: 12, fontWeight: 600, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span>SYSTEM NOTICE: {notice}</span>
            <button onClick={() => setNotice(null)} style={{ background: "transparent", border: "none", color: "#fff", cursor: "pointer", fontSize: 16 }}>×</button>
          </div>
        )}

        <div style={{ padding: "40px", maxWidth: 1400, margin: "0 auto" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 32, borderBottom: `1px solid ${T.border}`, paddingBottom: 24 }}>
            <div>
              <h1 style={{ fontSize: 28, fontWeight: 700, color: T.text, margin: "0 0 8px 0", letterSpacing: "-0.02em" }}>{cfg.meta?.title || "DASHBOARD"}</h1>
              <p style={{ fontSize: 14, color: T.muted, margin: 0 }}>{cfg.meta?.description}</p>
            </div>
            <div style={{ display: "flex", gap: 16, alignItems: "center" }}>

              <button
                onClick={() => navigate("/chatbot")}
                style={{
                  background: T.accent,
                  color: "#fff",
                  border: "none",
                  padding: "10px 16px",
                  borderRadius: 6,
                  cursor: "pointer",
                  fontSize: 12,
                  fontWeight: 600,
                  textTransform: "uppercase"
                }}
              >
                Launch AI Assistant
              </button>

              <div style={{ textAlign: "right" }}>
                <div style={{ fontSize: 11, color: T.faint, fontWeight: 600, textTransform: "uppercase", marginBottom: 4 }}>
                  Configuration State
                </div>
                <div style={{ fontSize: 13, color: T.text }}>
                  {cfg.rows?.length || 0} Rows · {wCount} Widgets
                </div>
              </div>

            </div>

          </div>

          <DashboardRenderer xml={mode === "static" ? MASTER_XML : xml} />

          {/* <div style={{ marginTop: 24 }}>
            <div style={{ fontSize: 16, fontWeight: 600, color: T.text, marginBottom: 16, borderBottom: `1px solid ${T.border}`, paddingBottom: 8 }}>
              Video Explorer
            </div>
            <VideoExplorerTable />
          </div> */}
        </div>
      </div>
    </div>
  );
}
