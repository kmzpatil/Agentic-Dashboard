import React from "react";
import { useNavigate } from "react-router-dom";
import { T } from "../../utils/theme";
import type { ParsedXML } from "../../store";
import DashboardRenderer from "../widgets/DashboardRenderer";

interface DashboardCanvasProps {
  notice: string | null;
  setNotice: (val: string | null) => void;
  cfg: ParsedXML;
  wCount: number;
  xml: string;
}

export default function DashboardCanvas({ notice, setNotice, cfg, wCount, xml }: DashboardCanvasProps) {
  const navigate = useNavigate();

  return (
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
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: 11, color: T.faint, fontWeight: 600, textTransform: "uppercase", marginBottom: 4 }}>Configuration State</div>
            <div style={{ fontSize: 13, color: T.text }}>{cfg.rows?.length || 0} Rows · {wCount} Widgets</div>
          </div>
        </div>

        <DashboardRenderer xml={xml} />
      </div>
    </div>
  );
}