import React from "react";
import { useNavigate } from "react-router-dom";
import { MASTER_XML } from "../../store";
import { parseXML } from "../../utils/parser";
import { T } from "../../utils/theme";
import DashboardRenderer from "../../components/widgets/DashboardRenderer";

export default function StaticDashboard() {
  const navigate = useNavigate();
  
  // We parse the MASTER_XML just to get the header title/description and widget counts
  const cfg = parseXML(MASTER_XML);
  const wCount = cfg.rows?.reduce((s, r) => s + r.widgets.length, 0) || 0;

  return (
    <div style={{ display: "flex", height: "100%", width: "100%" }}>
      
      {/* ── LEFT SIDEBAR (Locked State) ── */}
      <div style={{ width: 360, background: T.surface, borderRight: `1px solid ${T.border}`, display: "flex", flexDirection: "column", flexShrink: 0, zIndex: 10 }}>
        <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: 32, textAlign: "center" }}>
          <div style={{ width: 48, height: 48, borderRadius: "50%", background: T.bg, border: `1px solid ${T.border}`, display: "flex", alignItems: "center", justifyContent: "center", marginBottom: 16 }}>
            <span style={{ fontSize: 20, color: T.faint }}>⊞</span>
          </div>
          <div style={{ fontSize: 14, fontWeight: 600, color: T.text, marginBottom: 8 }}>Static Mode Active</div>
          <div style={{ fontSize: 12, color: T.muted, lineHeight: 1.5 }}>
            The dashboard is currently locked for viewing. Switch to Interactive mode to modify the layout using the Agent.
          </div>
        </div>
      </div>

      {/* ── MAIN DASHBOARD CANVAS ── */}
      <div style={{ flex: 1, overflowY: "auto", background: T.bg, position: "relative" }}>
        <div style={{ padding: "40px", maxWidth: 1400, margin: "0 auto" }}>
          
          {/* Header */}
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: 32, borderBottom: `1px solid ${T.border}`, paddingBottom: 24 }}>
            <div>
              <h1 style={{ fontSize: 28, fontWeight: 700, color: T.text, margin: "0 0 8px 0", letterSpacing: "-0.02em" }}>
                {cfg.meta?.title || "DASHBOARD"}
              </h1>
              <p style={{ fontSize: 14, color: T.muted, margin: 0 }}>
                {cfg.meta?.description}
              </p>
            </div>
            <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
              <button
                onClick={() => navigate("/chatbot")}
                style={{
                  background: T.accent, color: "#fff", border: "none", padding: "10px 16px",
                  borderRadius: 6, cursor: "pointer", fontSize: 12, fontWeight: 600, textTransform: "uppercase"
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

          {/* Render the static master XML directly */}
          <DashboardRenderer xml={MASTER_XML} />
          
        </div>
      </div>
    </div>
  );
}