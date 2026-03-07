import React, { useState, useRef, useEffect } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer, PieChart, Pie, Cell, RadarChart, Radar,
  PolarGrid, PolarAngleAxis, LineChart, Line,
} from "recharts";

// ════════════════════════════════════════════════════════════════
//  TYPES & INTERFACES
// ════════════════════════════════════════════════════════════════

interface Csv1Row {
  Channel: string;
  total_users: number;
  users_uploaded: number;
  users_created: number;
  users_published: number;
  total_uploaded_duration: number;
  total_created_duration: number;
  total_published_duration: number;
}

interface Csv2TypeRow {
  Type: string;
  count: number;
}

interface Csv2ChannelDistRow {
  channel_count: string;
  users: number;
}

// Using Record<string, string | number> for flexible CSV3 rows
type Csv3Row = Record<string, string | number>;

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
const _csv1: Csv1Row[] = [
  { Channel:"BBC World",   total_users:1240, users_uploaded:890, users_created:760, users_published:680, total_uploaded_duration:48200, total_created_duration:39100, total_published_duration:31400 },
  { Channel:"Al Jazeera",  total_users:980,  users_uploaded:710, users_created:620, users_published:540, total_uploaded_duration:37600, total_created_duration:29800, total_published_duration:24200 },
  { Channel:"Reuters TV",  total_users:760,  users_uploaded:530, users_created:480, users_published:390, total_uploaded_duration:28900, total_created_duration:22400, total_published_duration:17800 },
  { Channel:"CNN",         total_users:1120, users_uploaded:820, users_created:700, users_published:610, total_uploaded_duration:44100, total_created_duration:35600, total_published_duration:28700 },
  { Channel:"Sky News",    total_users:640,  users_uploaded:440, users_created:390, users_published:310, total_uploaded_duration:22300, total_created_duration:17900, total_published_duration:13400 },
  { Channel:"France 24",   total_users:520,  users_uploaded:360, users_created:300, users_published:260, total_uploaded_duration:18700, total_created_duration:14200, total_published_duration:11100 },
];

const DATA_STORE: Record<string, any> = {
  csv1: _csv1,
  csv1_aggregate: {
    total_users:              _csv1.reduce((s,x)=>s+x.total_users,0),
    users_uploaded:           _csv1.reduce((s,x)=>s+x.users_uploaded,0),
    users_created:            _csv1.reduce((s,x)=>s+x.users_created,0),
    users_published:          _csv1.reduce((s,x)=>s+x.users_published,0),
    total_uploaded_duration:  _csv1.reduce((s,x)=>s+x.total_uploaded_duration,0),
    total_created_duration:   _csv1.reduce((s,x)=>s+x.total_created_duration,0),
    total_published_duration: _csv1.reduce((s,x)=>s+x.total_published_duration,0),
  },
  csv1_duration_hours: _csv1.map(r=>({
    Channel: r.Channel,
    "Upload (h)":  Math.round(r.total_uploaded_duration/3600),
    "Create (h)":  Math.round(r.total_created_duration/3600),
    "Publish (h)": Math.round(r.total_published_duration/3600),
  })),
  csv2_types: [
    { Type:"Journalist",  count:1420 },
    { Type:"Editor",      count:870  },
    { Type:"Producer",    count:640  },
    { Type:"Anchor",      count:390  },
    { Type:"Researcher",  count:280  },
    { Type:"Contributor", count:660  },
  ] as Csv2TypeRow[],
  csv2_channel_dist: [
    { channel_count:"1",  users:1240 },
    { channel_count:"2",  users:980  },
    { channel_count:"3",  users:640  },
    { channel_count:"4",  users:290  },
    { channel_count:"5+", users:110  },
  ] as Csv2ChannelDistRow[],
  csv3: [
    { Channel:"BBC World",  news_bulletin:42, interview:28, debate:12, speech:8,  special_reports:18, press_conference:14, discussion_show:22, podcast:16, sports_show:6,  drama:3, in_brief:31 },
    { Channel:"Al Jazeera", news_bulletin:38, interview:24, debate:18, speech:11, special_reports:22, press_conference:10, discussion_show:18, podcast:8,  sports_show:4,  drama:2, in_brief:26 },
    { Channel:"Reuters TV", news_bulletin:56, interview:18, debate:6,  speech:4,  special_reports:14, press_conference:20, discussion_show:9,  podcast:4,  sports_show:2,  drama:0, in_brief:44 },
    { Channel:"CNN",        news_bulletin:48, interview:32, debate:20, speech:10, special_reports:24, press_conference:12, discussion_show:26, podcast:20, sports_show:10, drama:4, in_brief:36 },
    { Channel:"Sky News",   news_bulletin:36, interview:20, debate:14, speech:6,  special_reports:12, press_conference:8,  discussion_show:14, podcast:10, sports_show:8,  drama:2, in_brief:28 },
    { Channel:"France 24",  news_bulletin:30, interview:22, debate:16, speech:9,  special_reports:10, press_conference:6,  discussion_show:12, podcast:6,  sports_show:3,  drama:1, in_brief:22 },
  ] as Csv3Row[],
};
DATA_STORE.csv3_radar = DATA_STORE.csv3;

// ════════════════════════════════════════════════════════════════
//  MASTER XML
// ════════════════════════════════════════════════════════════════
const MASTER_XML: string = `<dashboard version="1.0" theme="light" cols="12">
  <meta>
    <title>Media Analytics</title>
    <description>Channel performance and content distribution metrics</description>
    <created>2026-03-07</created>
  </meta>

  <layout>

    <row id="r1" label="User Overview">
      <widget id="w1" type="kpi" col="1"  span="3" title="Total Users"     data-source="csv1_aggregate" metric="total_users"             color-scheme="blue"   />
      <widget id="w2" type="kpi" col="4"  span="3" title="Users Uploaded"  data-source="csv1_aggregate" metric="users_uploaded"          color-scheme="purple" />
      <widget id="w3" type="kpi" col="7"  span="3" title="Users Created"   data-source="csv1_aggregate" metric="users_created"           color-scheme="teal"   />
      <widget id="w4" type="kpi" col="10" span="3" title="Users Published" data-source="csv1_aggregate" metric="users_published"         color-scheme="green"  />
    </row>

    <row id="r2" label="Duration Overview">
      <widget id="w5" type="kpi" col="1" span="4" title="Upload Duration"  data-source="csv1_aggregate" metric="total_uploaded_duration"  color-scheme="blue"   unit="hours" />
      <widget id="w6" type="kpi" col="5" span="4" title="Create Duration"  data-source="csv1_aggregate" metric="total_created_duration"   color-scheme="purple" unit="hours" />
      <widget id="w7" type="kpi" col="9" span="4" title="Publish Duration" data-source="csv1_aggregate" metric="total_published_duration" color-scheme="teal"   unit="hours" />
    </row>

    <row id="r3" label="Channel Activity">
      <widget id="w8" type="bar-chart" col="1" span="7"
        title="User Activity by Channel"
        data-source="csv1"
        x-field="Channel"
        y-fields="users_uploaded,users_created,users_published"
        y-labels="Uploaded,Created,Published"
        color-scheme="multi"  
        show-legend="true"
        x-tick-short="true" />
      <widget id="w9" type="bar-chart" col="8" span="5"
        title="Duration by Channel (h)"
        data-source="csv1_duration_hours"
        x-field="Channel"
        y-fields="Upload (h),Create (h),Publish (h)"
        color-scheme="multi"
        show-legend="true"
        x-tick-short="true" />
    </row>

    <row id="r4" label="User Distribution">
      <widget id="w10" type="pie-chart" col="1" span="5"
        title="User Type Distribution"
        data-source="csv2_types"
        name-field="Type"
        value-field="count"
        color-scheme="multi"
        show-legend="true"
        variant="donut" />
      <widget id="w11" type="bar-chart" col="6" span="7"
        title="Users by Channel Count"
        data-source="csv2_channel_dist"
        x-field="channel_count"
        y-fields="users"
        y-labels="Users"
        color-scheme="blue"
        show-legend="false"
        x-label="No. of Channels" />
    </row>

    <row id="r5" label="Content Heatmap">
      <widget id="w12" type="heatmap" col="1" span="12"
        title="Content Type Distribution by Channel"
        data-source="csv3"
        row-field="Channel"
        col-fields="news_bulletin,interview,debate,speech,special_reports,press_conference,discussion_show,podcast,sports_show,drama,in_brief"
        col-labels="News Bulletin,Interview,Debate,Speech,Special Reports,Press Conference,Discussion Show,Podcast,Sports Show,Drama,In Brief"
        color-scheme="blue" />
    </row>

    <row id="r6" label="Channel Profiles">
      <widget id="w13" type="radar-grid" col="1" span="12"
        title="Channel Content Profile"
        data-source="csv3_radar"
        fields="news_bulletin,interview,debate,speech,special_reports,discussion_show"
        field-labels="Bulletin,Interview,Debate,Speech,Reports,Discussion"
        group-field="Channel"
        color-scheme="multi" />
    </row>

  </layout>
</dashboard>`;

// ════════════════════════════════════════════════════════════════
//  DESIGN TOKENS
// ════════════════════════════════════════════════════════════════
const T = {
  bg:      "#f7f8fa",
  surface: "#ffffff",
  border:  "#e8ecf4",
  text:    "#111827",
  muted:   "#6b7280",
  faint:   "#9ca3af",
  accent:  "#2563eb",
};

const PALETTE: Record<string, string> = { blue:"#2563eb", purple:"#7c3aed", teal:"#0891b2", green:"#059669", amber:"#d97706", red:"#dc2626" };
const MULTI: string[]   = ["#2563eb","#7c3aed","#0891b2","#059669","#d97706","#dc2626"];
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
      title:       doc.querySelector("meta > title")?.textContent || "Dashboard",
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
  } catch(e) { 
    return { error: String(e) }; 
  }
}

// ════════════════════════════════════════════════════════════════
//  SHARED PRIMITIVES
// ════════════════════════════════════════════════════════════════
function Card({ children, style = {} }: CardProps) {
  return <div style={{ background:T.surface, border:`1px solid ${T.border}`, borderRadius:8, padding:"16px 18px", height:"100%", ...style }}>{children}</div>;
}

function WHead({ title }: { title: string }) {
  return <div style={{ fontSize:12, fontWeight:600, color:T.text, marginBottom:12 }}>{title}</div>;
}

const RTip = ({ active, payload, label }: any) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background:"#fff", border:`1px solid ${T.border}`, borderRadius:6, padding:"7px 11px", fontSize:11, boxShadow:"0 4px 12px rgba(0,0,0,0.08)" }}>
      {label && <div style={{ fontWeight:600, color:T.text, marginBottom:3 }}>{label}</div>}
      {payload.map((p: any, i: number) =>(
        <div key={i} style={{ color:p.color, display:"flex", gap:8 }}>
          <span>{p.name}:</span><span style={{ fontWeight:600 }}>{typeof p.value==="number" ? p.value.toLocaleString():p.value}</span>
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
    <div style={{ background:"#fef2f2", border:`1px dashed #fca5a5`, borderRadius:8, padding:"14px", height:"100%", display:"flex", alignItems:"center", gap:8 }}>
      <span style={{ color:"#ef4444" }}>⚠</span>
      <span style={{ fontSize:11, color:"#b91c1c" }}>{msg}</span>
    </div>
  );
}

function WKpi({ a }: WidgetProps) {
  const src = DATA_STORE[a["data-source"]];
  if (!src) return <ErrW msg={`Unknown data-source: ${a["data-source"]}`} />;
  
  let val = src[a.metric];
  if (a.unit === "hours") val = `${Math.round(val/3600).toLocaleString()}h`;
  else val = typeof val === "number" ? val.toLocaleString() : "—";
  
  const c = scheme(a["color-scheme"] || "blue");
  return (
    <div style={{ background:T.surface, border:`1px solid ${T.border}`, borderTop:`3px solid ${c}`, borderRadius:8, padding:"16px 18px", height:"100%" }}>
      <div style={{ fontSize:10, color:T.muted, letterSpacing:0.8, textTransform:"uppercase", marginBottom:6 }}>{a.title}</div>
      <div style={{ fontSize:24, fontWeight:700, color:T.text, letterSpacing:-0.5 }}>{val}</div>
    </div>
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
      <ResponsiveContainer width="100%" height={195}>
        <BarChart data={src} margin={{ top:2, right:6, left:-14, bottom:a["x-label"]?14:0 }} barCategoryGap="32%">
          <CartesianGrid strokeDasharray="3 3" stroke={T.border} vertical={false} />
          <XAxis dataKey={a["x-field"]} tick={{ fontSize:10, fill:T.muted }} tickLine={false} axisLine={false}
            tickFormatter={(v: any) => a["x-tick-short"]==="true" ? String(v).split(" ")[0] : v}
            label={a["x-label"] ? { value:a["x-label"], position:"insideBottom", offset:-6, fontSize:10, fill:T.faint } : undefined} />
          <YAxis tick={{ fontSize:10, fill:T.muted }} tickLine={false} axisLine={false} />
          <Tooltip content={<RTip />} />
          {showLeg && <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize:10, paddingTop:6 }} />}
          {yFields.map((f, i) => (
            <Bar key={f} dataKey={f} name={yLabels[i]||f} fill={scheme(a["color-scheme"]||"blue", i)} radius={[3,3,0,0]} />
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
      <div style={{ display:"flex", alignItems:"center", gap:16 }}>
        <ResponsiveContainer width={150} height={150}>
          <PieChart>
            <Pie data={src} dataKey={vF} nameKey={nF} cx="50%" cy="50%"
              innerRadius={donut ? 40 : 0} outerRadius={65} paddingAngle={2}>
              {src.map((_: any, i: number) => <Cell key={i} fill={MULTI[i % MULTI.length]} />)}
            </Pie>
            <Tooltip content={<RTip />} />
          </PieChart>
        </ResponsiveContainer>
        <div style={{ flex:1, display:"flex", flexDirection:"column", gap:6 }}>
          {src.map((row: any, i: number) =>(
            <div key={i} style={{ display:"flex", alignItems:"center", gap:7 }}>
              <div style={{ width:7, height:7, borderRadius:2, background:MULTI[i % MULTI.length], flexShrink:0 }} />
              <span style={{ fontSize:11, color:T.muted, flex:1 }}>{row[nF]}</span>
              <span style={{ fontSize:11, fontWeight:600, color:T.text }}>{Number(row[vF]).toLocaleString()}</span>
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
  
  const cols   = a["col-fields"].split(",");
  const labels = a["col-labels"] ? a["col-labels"].split(",") : cols;
  const rowF   = a["row-field"];
  const maxV   = Math.max(...src.flatMap((r: any) => cols.map((c: string) => Number(r[c]) || 0)));
  
  const heat = (v: number) => {
    const t = v/maxV;
    if (t < 0.2) return { bg:"#eff6ff", fg:T.text };
    if (t < 0.4) return { bg:"#bfdbfe", fg:T.text };
    if (t < 0.6) return { bg:"#93c5fd", fg:T.text };
    if (t < 0.75) return { bg:"#3b82f6", fg:"#fff"  };
    return { bg:"#1d4ed8", fg:"#fff"  };
  };

  return (
    <Card>
      <WHead title={a.title} />
      <div style={{ overflowX:"auto" }}>
        <table style={{ width:"100%", borderCollapse:"collapse", fontSize:11 }}>
          <thead>
            <tr>
              <th style={{ textAlign:"left", padding:"6px 10px", color:T.muted, fontWeight:500, borderBottom:`1px solid ${T.border}`, minWidth:88 }}>Channel</th>
              {labels.map((l, i) =>(
                <th key={i} style={{ textAlign:"center", padding:"4px 4px", color:T.muted, fontWeight:500, borderBottom:`1px solid ${T.border}`, minWidth:56, fontSize:10, lineHeight:1.3 }}>
                  {l.split(" ").map((w, j) => <div key={j}>{w}</div>)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {src.map((row: any, ri: number) =>(
              <tr key={ri}>
                <td style={{ padding:"8px 10px", fontWeight:500, color:T.text, borderBottom:`1px solid ${T.border}` }}>{row[rowF]}</td>
                {cols.map((c: string, ci: number) => { 
                  const v = Number(row[c]) || 0; 
                  const {bg, fg} = heat(v); 
                  return (
                    <td key={ci} style={{ textAlign:"center", padding:"8px 4px", borderBottom:`1px solid ${T.border}`, background:bg, color:fg, fontWeight: v/maxV>0.4 ? 600 : 400 }}>{v}</td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ display:"flex", alignItems:"center", gap:4, marginTop:8, justifyContent:"flex-end" }}>
          <span style={{ fontSize:10, color:T.faint }}>Low</span>
          {["#eff6ff","#bfdbfe","#93c5fd","#3b82f6","#1d4ed8"].map((c, i) =>(
            <div key={i} style={{ width:16, height:9, background:c, borderRadius:2 }} />
          ))}
          <span style={{ fontSize:10, color:T.faint }}>High</span>
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
      <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:10 }}>
        {src.map((row: any, ri: number) => {
          const data = fields.map((f: string, fi: number) => ({ s:labels[fi], v:row[f] || 0 }));
          return (
            <div key={ri} style={{ textAlign:"center" }}>
              <div style={{ fontSize:11, fontWeight:600, color:T.text, marginBottom:2 }}>{row[gF]}</div>
              <ResponsiveContainer width="100%" height={130}>
                <RadarChart data={data} margin={{ top:4,right:16,bottom:4,left:16 }}>
                  <PolarGrid stroke={T.border} />
                  <PolarAngleAxis dataKey="s" tick={{ fontSize:9, fill:T.muted }} />
                  <Radar dataKey="v" stroke={MULTI[ri % MULTI.length]} fill={MULTI[ri % MULTI.length]} fillOpacity={0.15} strokeWidth={1.5} />
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
      <ResponsiveContainer width="100%" height={195}>
        <LineChart data={src} margin={{ top:2,right:6,left:-14,bottom:0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke={T.border} vertical={false} />
          <XAxis dataKey={a["x-field"]} tick={{ fontSize:10,fill:T.muted }} tickLine={false} axisLine={false} />
          <YAxis tick={{ fontSize:10,fill:T.muted }} tickLine={false} axisLine={false} />
          <Tooltip content={<RTip />} />
          <Legend iconType="circle" iconSize={7} wrapperStyle={{ fontSize:10, paddingTop:6 }} />
          {yF.map((f, i) =>(
            <Line key={f} type="monotone" dataKey={f} name={yL[i]||f}
              stroke={scheme(a["color-scheme"]||"blue", i)} strokeWidth={2} dot={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </Card>
  );
}

const REGISTRY: Record<string, React.FC<WidgetProps>> = {
  "kpi":        WKpi,
  "bar-chart":  WBar,
  "pie-chart":  WPie,
  "heatmap":    WHeatmap,
  "radar-grid": WRadarGrid,
  "line-chart": WLine,
};

// ════════════════════════════════════════════════════════════════
//  DASHBOARD RENDERER
// ════════════════════════════════════════════════════════════════
function DashboardRenderer({ xml }: { xml: string }) {
  const cfg = parseXML(xml);
  if (cfg.error) return (
    <div style={{ background:"#fef2f2", border:`1px solid #fca5a5`, borderRadius:8, padding:18, fontSize:12, color:"#b91c1c" }}>
      <strong>XML Error</strong><br />{cfg.error}
    </div>
  );
  
  return (
    <div style={{ display:"flex", flexDirection:"column", gap:18 }}>
      {cfg.rows?.map(row => (
        <div key={row.id}>
          {row.label && (
            <div style={{ fontSize:10, color:T.faint, letterSpacing:0.8, textTransform:"uppercase", marginBottom:8 }}>{row.label}</div>
          )}
          <div style={{ display:"grid", gridTemplateColumns:"repeat(12,1fr)", gap:12 }}>
            {row.widgets.map((w, index) => {
              const Comp = REGISTRY[w.type];
              const col  = parseInt(w.col) || 1;
              const span = parseInt(w.span) || 4;
              return (
                <div key={w.id || index} style={{ gridColumn:`${col} / span ${span}` }}>
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
    <div style={{ fontFamily:"'JetBrains Mono','Fira Code',monospace", fontSize:11, lineHeight:1.9, overflowX:"auto" }}>
      {xml.trim().split("\n").map((raw, i) => {
        const esc = raw.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
        const hi  = esc
          .replace(/(&lt;\/?)([\w-]+)/g, (_, p, t) => `${p}<span style="color:#2563eb;font-weight:600">${t}</span>`)
          .replace(/([\w-]+)=&quot;([^&]*)&quot;/g, (_, a, v) => `<span style="color:#7c3aed">${a}</span>=<span style="color:#059669">"${v}"</span>`)
          .replace(/&lt;!--([\s\S]*?)--&gt;/g, (_, c) => `<span style="color:#9ca3af">&lt;!--${c}--&gt;</span>`);
        return (
          <div key={i} style={{ display:"flex" }}>
            <span style={{ color:"#d1d5db", userSelect:"none", marginRight:14, minWidth:26, textAlign:"right", flexShrink:0 }}>{i+1}</span>
            <span dangerouslySetInnerHTML={{ __html:hi }} />
          </div>
        );
      })}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
//  AGENT SYSTEM PROMPT
// ════════════════════════════════════════════════════════════════
const SYSTEM_PROMPT: string = `You are a dashboard XML configuration assistant for a media analytics platform.
Your ONLY output is a complete valid XML document — no explanation, no markdown, no code fences.
Output must start with <dashboard and end with </dashboard>.

SUPPORTED WIDGET TYPES:
- kpi          → data-source, metric, title, color-scheme (blue|purple|teal|green|amber|red), [unit=hours]
- bar-chart    → data-source, x-field, y-fields (comma list), title, [y-labels], [color-scheme (blue|multi|...)], [show-legend=true|false], [x-tick-short=true], [x-label]
- pie-chart    → data-source, name-field, value-field, title, [color-scheme=multi], [show-legend=true], [variant=donut]
- heatmap      → data-source, row-field, col-fields (comma list), col-labels (comma list), title, [color-scheme=blue]
- radar-grid   → data-source, fields (comma list), field-labels (comma list), group-field, title, [color-scheme=multi]
- line-chart   → data-source, x-field, y-fields, title, [y-labels], [color-scheme]

AVAILABLE DATA SOURCES:
- csv1                → Channel, total_users, users_uploaded, users_created, users_published, total_uploaded_duration, total_created_duration, total_published_duration
- csv1_aggregate      → single aggregate object, same fields as csv1 (use for kpi widgets)
- csv1_duration_hours → Channel, "Upload (h)", "Create (h)", "Publish (h)"
- csv2_types          → Type, count
- csv2_channel_dist   → channel_count, users
- csv3                → Channel, news_bulletin, interview, debate, speech, special_reports, press_conference, discussion_show, podcast, sports_show, drama, in_brief
- csv3_radar          → same as csv3

RULES:
- Grid has 12 cols. col + span must not exceed 13.
- All widget IDs must be unique. All row IDs must be unique.
- Always return the FULL updated dashboard XML.
- If something is unavailable, add <notice message="reason" /> inside <meta> and return XML unchanged.`;

// ════════════════════════════════════════════════════════════════
//  INTERACTIVE DASHBOARD
// ════════════════════════════════════════════════════════════════
function InteractiveDashboard() {
  const [xml, setXml]           = useState<string>(MASTER_XML);
  const [history, setHistory]   = useState<string[]>([MASTER_XML]);
  const [msgs, setMsgs]         = useState<ChatMessage[]>([
    { role:"agent", text:"Hi! I can update this dashboard — add, remove, or change widgets. Try a suggestion below or type your own." }
  ]);
  const [input, setInput]       = useState<string>("");
  const [status, setStatus]     = useState<"idle" | "thinking" | "error">("idle");
  const [rightTab, setRightTab] = useState<string>("chat");
  const [notice, setNotice]     = useState<string | null>(null);
  
  const endRef  = useRef<HTMLDivElement>(null);
  const inputRef= useRef<HTMLInputElement>(null);

  useEffect(()=>{ endRef.current?.scrollIntoView({ behavior:"smooth" }); }, [msgs]);

  const cfg = parseXML(xml);
  const wCount = cfg.rows?.reduce((s, r) => s + r.widgets.length, 0) || 0;

  async function send() {
    const msg = input.trim();
    if (!msg || status === "thinking") return;
    setInput("");
    setMsgs(p => [...p, { role:"user", text:msg }]);
    setStatus("thinking");
    setNotice(null);
    
    try {
      const apiMsgs = [
        ...msgs.filter(m => !m.isErr).map(m => ({
          role: m.role === "user" ? "user" : "assistant",
          content: m.role === "user" ? m.text : (m.xml || m.text),
        })),
        { role:"user", content:`Current XML:\n${xml}\n\nRequest: ${msg}` }
      ];
      
      const res  = await fetch("https://api.anthropic.com/v1/messages", {
        method:"POST",
        headers:{ "Content-Type":"application/json" },
        body: JSON.stringify({ model:"claude-sonnet-4-20250514", max_tokens:4000, system:SYSTEM_PROMPT, messages:apiMsgs }),
      });
      
      const data = await res.json();
      const raw  = data.content?.map((b: any) => b.text || "").join("") || "";
      const match = raw.match(/<dashboard[\s\S]*<\/dashboard>/);
      
      if (!match) {
        setMsgs(p => [...p, { role:"agent", text:raw || "No XML returned.", isErr:true }]);
        setStatus("error"); return;
      }
      
      const newXml = match[0];
      const parsed = parseXML(newXml);
      
      if (parsed.error) {
        setMsgs(p => [...p, { role:"agent", text:`Validation failed: ${parsed.error}`, isErr:true }]);
        setStatus("error"); return;
      }
      
      if (parsed.notice) {
        setNotice(parsed.notice);
        setMsgs(p => [...p, { role:"agent", text:`⚠ ${parsed.notice}` }]);
        setStatus("idle"); return;
      }
      
      setHistory(h => [...h, newXml]);
      setXml(newXml);
      
      const nw = parsed.rows?.reduce((s, r) => s + r.widgets.length, 0) || 0;
      const diff= nw - wCount;
      const ds  = diff > 0 ? ` (+${diff} widget${diff > 1 ? "s" : ""})`
                : diff < 0 ? ` (${diff} widget${Math.abs(diff) > 1 ? "s" : ""})` : "";
                
      setMsgs(p => [...p, { role:"agent", text:`Updated${ds}. ${parsed.rows?.length} rows, ${nw} widgets.`, xml:newXml }]);
      setStatus("idle");
    } catch(e) {
      const errorMsg = e instanceof Error ? e.message : String(e);
      setMsgs(p => [...p, { role:"agent", text:`Error: ${errorMsg}`, isErr:true }]);
      setStatus("error");
    }
  }

  function undo() {
    if (history.length <= 1) return;
    const prev = history[history.length - 2];
    setHistory(h => h.slice(0, -1));
    setXml(prev);
    setMsgs(p => [...p, { role:"agent", text:"Reverted to previous version." }]);
  }

  const SUGG: string[] = [
    "Add a line chart showing total users by channel",
    "Remove the radar grid",
    "Show a donut chart for channel user counts",
    "Add a KPI for average upload duration",
  ];

  return (
    <div style={{ display:"grid", gridTemplateColumns:"1fr 336px", gap:16, alignItems:"start" }}>

      {/* ── Dashboard panel ── */}
      <div>
        {notice && (
          <div style={{ marginBottom:12, padding:"9px 14px", background:"#fffbeb", border:`1px solid #fcd34d`, borderRadius:6, fontSize:11, color:"#92400e", display:"flex", gap:8 }}>
            <span>⚠</span><span style={{ flex:1 }}>{notice}</span>
            <button onClick={() => setNotice(null)} style={{ background:"none", border:"none", cursor:"pointer", color:"#92400e", fontSize:14, lineHeight:1 }}>×</button>
          </div>
        )}
        <div style={{ background:T.surface, border:`1px solid ${T.border}`, borderRadius:8, padding:"18px 20px" }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:20, gap:12 }}>
            <div>
              <div style={{ fontSize:14, fontWeight:700, color:T.text }}>{cfg.meta?.title}</div>
              <div style={{ fontSize:11, color:T.muted, marginTop:1 }}>{cfg.meta?.description}</div>
            </div>
            <div style={{ display:"flex", gap:8, alignItems:"center", flexShrink:0 }}>
              <span style={{ fontSize:10, color:T.faint }}>{cfg.rows?.length} rows · {wCount} widgets</span>
              <button onClick={undo} disabled={history.length <= 1} style={{
                fontSize:11, padding:"4px 10px", borderRadius:5, border:`1px solid ${T.border}`,
                background:history.length <= 1 ? T.bg : T.surface,
                color:history.length <= 1 ? T.faint : T.muted, cursor:history.length <= 1 ? "not-allowed" : "pointer",
              }}>↩ Undo</button>
            </div>
          </div>
          <DashboardRenderer xml={xml} />
        </div>
      </div>

      {/* ── Right panel ── */}
      <div style={{
        background:T.surface, border:`1px solid ${T.border}`, borderRadius:8,
        display:"flex", flexDirection:"column",
        height:"calc(100vh - 116px)", minHeight:520,
        position:"sticky", top:64,
      }}>
        {/* Tabs */}
        <div style={{ display:"flex", borderBottom:`1px solid ${T.border}`, flexShrink:0 }}>
          {[["chat","💬 Chat"], ["xml","📄 XML"]].map(([k, lbl]) =>(
            <button key={k} onClick={() => setRightTab(k)} style={{
              flex:1, padding:"11px 0", border:"none", cursor:"pointer",
              background:T.surface,
              borderBottom: rightTab === k ? `2px solid ${T.accent}` : `2px solid transparent`,
              color: rightTab === k ? T.accent : T.muted,
              fontSize:12, fontWeight: rightTab === k ? 600 : 400,
            }}>{lbl}</button>
          ))}
        </div>

        {rightTab === "chat" ? (<>
          {/* Suggestion chips */}
          <div style={{ padding:"10px 12px", borderBottom:`1px solid ${T.border}`, display:"flex", flexWrap:"wrap", gap:5, flexShrink:0 }}>
            {SUGG.map(s =>(
              <button key={s} onClick={() => { setInput(s); inputRef.current?.focus(); }} style={{
                fontSize:10, padding:"3px 8px", background:"#eff6ff", color:T.accent,
                border:`1px solid #dbeafe`, borderRadius:4, cursor:"pointer", textAlign:"left",
              }}>{s}</button>
            ))}
          </div>

          {/* Messages */}
          <div style={{ flex:1, overflowY:"auto", padding:"14px 13px", display:"flex", flexDirection:"column", gap:10 }}>
            {msgs.map((m, i) =>(
              <div key={i} style={{ display:"flex", flexDirection:"column", alignItems: m.role === "user" ? "flex-end" : "flex-start" }}>
                <div style={{ fontSize:9, color:T.faint, marginBottom:2 }}>{m.role === "user" ? "You" : "Agent"}</div>
                <div style={{
                  maxWidth:"92%", padding:"8px 11px", borderRadius:7, fontSize:11.5, lineHeight:1.6,
                  background: m.role === "user" ? T.accent : m.isErr ? "#fef2f2" : "#f3f4f6",
                  color: m.role === "user" ? "#fff" : m.isErr ? "#b91c1c" : T.text,
                  borderBottomRightRadius: m.role === "user" ? 2 : 7,
                  borderBottomLeftRadius:  m.role === "agent" ? 2 : 7,
                }}>{m.text}</div>
              </div>
            ))}
            {status === "thinking" && (
              <div style={{ display:"flex", flexDirection:"column", alignItems:"flex-start" }}>
                <div style={{ fontSize:9, color:T.faint, marginBottom:2 }}>Agent</div>
                <div style={{ padding:"10px 14px", background:"#f3f4f6", borderRadius:7, borderBottomLeftRadius:2, display:"flex", gap:4 }}>
                  {[0, 1, 2].map(i =>(
                    <div key={i} style={{ width:5, height:5, borderRadius:"50%", background:T.faint,
                      animation:"db 1.2s infinite ease-in-out", animationDelay:`${i * 0.2}s` }} />
                  ))}
                </div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Input */}
          <div style={{ padding:"11px 12px", borderTop:`1px solid ${T.border}`, flexShrink:0 }}>
            <div style={{ display:"flex", gap:7 }}>
              <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && send()}
                placeholder="Ask the agent to update the dashboard…"
                style={{ flex:1, padding:"8px 11px", borderRadius:6, border:`1px solid ${T.border}`,
                  fontSize:11.5, color:T.text, outline:"none", background:T.bg, fontFamily:"inherit" }} />
              <button onClick={send} disabled={status === "thinking"} style={{
                padding:"8px 13px", borderRadius:6, border:"none",
                background: status === "thinking" ? T.border : T.accent,
                color: status === "thinking" ? T.muted : "#fff",
                fontSize:12, cursor: status === "thinking" ? "not-allowed" : "pointer", fontWeight:500,
              }}>Send</button>
            </div>
            <div style={{ fontSize:10, color:T.faint, marginTop:5 }}>
              Agent rewrites XML → validates → re-renders live
            </div>
          </div>
        </>) : (
          /* XML tab */
          <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>
            <div style={{ padding:"9px 13px", borderBottom:`1px solid ${T.border}`, display:"flex", justifyContent:"space-between", alignItems:"center", flexShrink:0 }}>
              <span style={{ fontSize:11, color:T.muted }}>dashboard.xml · {xml.split("\n").length} lines</span>
              <div style={{ display:"flex", gap:5 }}>
                <button onClick={undo} disabled={history.length <= 1} style={{ fontSize:10, padding:"3px 9px", border:`1px solid ${T.border}`, borderRadius:4, background:T.surface, color:T.muted, cursor:"pointer" }}>↩ Undo</button>
                <button onClick={() => navigator.clipboard?.writeText(xml)} style={{ fontSize:10, padding:"3px 9px", border:`1px solid ${T.border}`, borderRadius:4, background:T.surface, color:T.muted, cursor:"pointer" }}>Copy</button>
              </div>
            </div>
            <div style={{ flex:1, overflowY:"auto", padding:"13px 15px", background:"#f8faff" }}>
              <XMLViewer xml={xml} />
            </div>
          </div>
        )}
      </div>

      <style>{`@keyframes db{0%,80%,100%{transform:translateY(0);opacity:.5}40%{transform:translateY(-5px);opacity:1}}`}</style>
    </div>
  );
}

// ════════════════════════════════════════════════════════════════
//  APP SHELL
// ════════════════════════════════════════════════════════════════
export default function App() {
  const [mode, setMode] = useState<"static" | "interactive">("static");
  
  return (
    <div style={{ minHeight:"100vh", background:T.bg, fontFamily:"'DM Sans','Segoe UI',sans-serif" }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
        *{box-sizing:border-box;margin:0;padding:0}
        ::-webkit-scrollbar{width:5px;height:5px}
        ::-webkit-scrollbar-track{background:transparent}
        ::-webkit-scrollbar-thumb{background:#e2e8f0;border-radius:3px}
      `}</style>

      {/* Topbar */}
      <div style={{
        background:T.surface, borderBottom:`1px solid ${T.border}`,
        padding:"0 26px", height:52, display:"flex", alignItems:"center",
        justifyContent:"space-between", position:"sticky", top:0, zIndex:200,
      }}>
        <div style={{ display:"flex", alignItems:"center", gap:10 }}>
          <div style={{ width:24, height:24, background:T.accent, borderRadius:5, display:"flex", alignItems:"center", justifyContent:"center" }}>
            <span style={{ color:"#fff", fontSize:10, fontWeight:700 }}>PS</span>
          </div>
          <span style={{ fontSize:13, fontWeight:600, color:T.text }}>PS for Data</span>
          <div style={{ width:1, height:16, background:T.border }} />
          <span style={{ fontSize:12, color:T.muted }}>Media Analytics Dashboard</span>
        </div>

        <div style={{ display:"flex", alignItems:"center", gap:9 }}>
          <span style={{ fontSize:12, color: mode === "static" ? T.text : T.muted, fontWeight: mode === "static" ? 600 : 400 }}>Static</span>
          <div onClick={() => setMode(m => m === "static" ? "interactive" : "static")} style={{
            width:42, height:22, borderRadius:11,
            background: mode === "interactive" ? T.accent : "#d1d5db",
            cursor:"pointer", position:"relative", transition:"background 0.2s",
          }}>
            <div style={{
              position:"absolute", top:3, left: mode === "interactive" ? 21 : 3,
              width:16, height:16, borderRadius:"50%", background:"#fff",
              boxShadow:"0 1px 3px rgba(0,0,0,0.15)", transition:"left 0.18s",
            }} />
          </div>
          <span style={{ fontSize:12, color: mode === "interactive" ? T.text : T.muted, fontWeight: mode === "interactive" ? 600 : 400 }}>Interactive</span>
        </div>
      </div>

      {mode === "interactive" && (
        <div style={{ background:"#eff6ff", borderBottom:`1px solid #bfdbfe`, padding:"6px 26px", fontSize:11, color:"#1d4ed8" }}>
          ⚡ <strong>Interactive mode —</strong> Chat with the agent to update the dashboard. XML drives the layout. Changes render live.
        </div>
      )}

      <div style={{ padding:"22px 26px" }}>
        {mode === "static"
          ? <DashboardRenderer xml={MASTER_XML} />
          : <InteractiveDashboard />
        }
      </div>
    </div>
  );
}