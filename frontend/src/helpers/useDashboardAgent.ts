import { useState } from "react";
import { MASTER_XML,type ChatMessage, updateDataStore } from "../store";
import { parseXML, buildDataStoreFromResponse } from "../utils/parser";

export function useDashboardAgent() {
  const [xml, setXml] = useState<string>(MASTER_XML);
  const [history, setHistory] = useState<string[]>([MASTER_XML]);
  const [msgs, setMsgs] = useState<ChatMessage[]>([
    { role: "agent", text: "SYSTEM ONLINE. I can modify dashboard configurations via XML. Select a prompt below or type instructions." }
  ]);
  const [status, setStatus] = useState<"idle" | "thinking" | "error">("idle");
  const [notice, setNotice] = useState<string | null>(null);

  // Derived state that the UI needs for the header
  const cfg = parseXML(xml);
  const wCount = cfg.rows?.reduce((s, r) => s + r.widgets.length, 0) || 0;

  async function send(msg: string) {
    if (!msg || status === "thinking") return;
    
    setMsgs(p => [...p, { role: "user", text: msg }]);
    setStatus("thinking");
    setNotice(null);

    try {
      const res = await fetch("/api/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
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

      // Update global Recharts data store
      updateDataStore(buildDataStoreFromResponse(newXml, data.chart_data || {}));

      // Update history and UI state
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

  return {
    xml, setXml, history, msgs, status, notice, setNotice, send, undo, cfg, wCount
  };
}