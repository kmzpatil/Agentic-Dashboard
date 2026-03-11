import React from "react";
import { T } from "../../utils/theme";
import type { ChatMessage } from "../../store";

interface AgentPanelProps {
  rightTab: string;
  setRightTab: (tab: string) => void;
  input: string;
  setInput: (val: string) => void;
  handleSend: () => void;
  msgs: ChatMessage[];
  status: "idle" | "thinking" | "error";
  endRef: any;
  inputRef: any;
  xml: string;
  setXml: (val: string) => void;
  undo: () => void;
  historyLength: number;
}

const SUGG = [
  "Build an executive dashboard with 4 key KPIs",
  "Show top 10 channels by published duration",
  "Compare user distribution by role as a donut chart",
];

export default function AgentPanel(props: AgentPanelProps) {
  const { 
    rightTab, setRightTab, input, setInput, handleSend, 
    msgs, status, endRef, inputRef, xml, setXml, undo, historyLength 
  } = props;

  return (
    <div style={{ width: 360, background: T.surface, borderRight: `1px solid ${T.border}`, display: "flex", flexDirection: "column", zIndex: 10 }}>
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
              <button key={s} onClick={() => { setInput(s); inputRef?.current?.focus(); }} style={{ fontSize: 10, padding: "6px 10px", background: T.bg, color: T.muted, border: `1px solid ${T.border}`, borderRadius: 4, cursor: "pointer" }}>{s}</button>
            ))}
          </div>

          {/* Chat Log */}
          <div style={{ flex: 1, overflowY: "auto", padding: "16px", display: "flex", flexDirection: "column", gap: 16 }}>
            {msgs.map((m, i) => (
              <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: m.role === "user" ? "flex-end" : "flex-start" }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: T.faint, marginBottom: 4, textTransform: "uppercase" }}>{m.role === "user" ? "User" : "System"}</div>
                <div style={{ maxWidth: "90%", padding: "12px 14px", borderRadius: 6, fontSize: 13, lineHeight: 1.5, background: m.role === "user" ? T.border : m.isErr ? "#450a0a" : T.bg, color: m.isErr ? T.danger : T.text, border: m.isErr ? `1px solid ${T.danger}` : `1px solid ${m.role === "user" ? "transparent" : T.border}` }}>{m.text}</div>
              </div>
            ))}
            {status === "thinking" && (
              <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start" }}>
                <div style={{ fontSize: 10, fontWeight: 600, color: T.faint, marginBottom: 4 }}>SYSTEM</div>
                <div style={{ padding: "12px 16px", background: T.bg, borderRadius: 6, border: `1px solid ${T.border}`, color: T.accent, fontSize: 12, fontWeight: 600, animation: "pulse 1.5s infinite" }}>Processing Request...</div>
              </div>
            )}
            <div ref={endRef} />
          </div>

          {/* Input Area */}
          <div style={{ padding: "16px", borderTop: `1px solid ${T.border}`, background: T.bg }}>
            <div style={{ display: "flex", gap: 8 }}>
              <input ref={inputRef} value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && handleSend()} placeholder="Enter command..." style={{ flex: 1, padding: "10px 14px", borderRadius: 4, border: `1px solid ${T.border}`, fontSize: 13, color: T.text, outline: "none", background: T.surface, fontFamily: "inherit" }} />
              <button onClick={handleSend} disabled={status === "thinking"} style={{ padding: "0 16px", borderRadius: 4, border: "none", background: status === "thinking" ? T.border : T.accent, color: "#fff", fontSize: 12, fontWeight: 600, cursor: status === "thinking" ? "not-allowed" : "pointer", textTransform: "uppercase" }}>Run</button>
            </div>
          </div>
        </>
      ) : (
        /* XML Editable Tab */
        <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
          <div style={{ padding: "12px 16px", borderBottom: `1px solid ${T.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 11, color: T.muted }}>dashboard.xml</span>
            <div style={{ display: "flex", gap: 8 }}>
              <button onClick={undo} disabled={historyLength <= 1} style={{ fontSize: 10, padding: "4px 8px", background: T.bg, border: `1px solid ${T.border}`, color: T.muted, cursor: "pointer", borderRadius: 4 }}>UNDO</button>
              <button onClick={() => navigator.clipboard?.writeText(xml)} style={{ fontSize: 10, padding: "4px 8px", background: T.bg, border: `1px solid ${T.border}`, color: T.text, cursor: "pointer", borderRadius: 4 }}>COPY</button>
            </div>
          </div>
          <textarea 
            value={xml}
            onChange={(e) => setXml(e.target.value)}
            style={{ 
              flex: 1, padding: "16px", background: "#0a0a0a", color: T.text, 
              fontFamily: "'JetBrains Mono','Fira Code',monospace", fontSize: 11, 
              lineHeight: 1.6, border: "none", outline: "none", resize: "none",
              whiteSpace: "pre" 
            }} 
            spellCheck={false}
          />
        </div>
      )}
    </div>
  );
}