import React, { useState } from "react";
import { NavLink } from "react-router-dom";
import { T } from "../utils/theme";

export default function Sidebar() {
  const [isOpen, setIsOpen] = useState(true);

  // Example channel data
  const channels = [
    { id: "yt", label: "YT", color: "#FF0000" },
    { id: "ig", label: "IG", color: "#E1306C" },
    { id: "tk", label: "TK", color: "#00f2fe" },
  ];

  return (
    <div style={{ display: "flex", height: "100%", zIndex: 50, flexShrink: 0 }}>
      {/* ── CHANNEL ICON STRIP (Always Visible) ── */}
      <div style={{ width: 64, background: "#050505", borderRight: `1px solid ${T.border}`, display: "flex", flexDirection: "column", alignItems: "center", padding: "16px 0", gap: 20 }}>
        <button 
          onClick={() => setIsOpen(!isOpen)} 
          style={{ background: "transparent", border: "none", color: T.muted, cursor: "pointer", fontSize: 18, padding: 8 }}
        >
          {isOpen ? "◀" : "▶"}
        </button>

        <hr style={{ width: "40%", borderColor: T.border, margin: 0 }} />

        <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          {channels.map((ch) => (
            <div key={ch.id} title={ch.label} style={{ width: 40, height: 40, borderRadius: "50%", background: T.surface, border: `1px solid ${T.border}`, display: "flex", alignItems: "center", justifyContent: "center", cursor: "pointer" }}>
              <span style={{ fontSize: 12, fontWeight: 700, color: ch.color }}>{ch.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ── NAVIGATION MENU (Closable) ── */}
      {isOpen && (
        <div style={{ width: 240, background: T.surface, borderRight: `1px solid ${T.border}`, display: "flex", flexDirection: "column" }}>
          <div style={{ padding: "24px", borderBottom: `1px solid ${T.border}` }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: T.text, letterSpacing: "0.02em" }}>PS FOR DATA</div>
            <div style={{ fontSize: 11, color: T.muted, textTransform: "uppercase", letterSpacing: "0.05em" }}>Workspace</div>
          </div>

          <div style={{ padding: "16px", display: "flex", flexDirection: "column", gap: 8 }}>
            {[
              { path: "/dynamic", label: "Interactive Agent" },
              { path: "/static", label: "Static Overview" }
            ].map((link) => (
              <NavLink
                key={link.path}
                to={link.path}
                style={({ isActive }) => ({
                  padding: "10px 14px",
                  borderRadius: 6,
                  textDecoration: "none",
                  fontSize: 13,
                  fontWeight: 600,
                  background: isActive ? T.accent : "transparent",
                  color: isActive ? "#fff" : T.muted,
                })}
              >
                {link.label}
              </NavLink>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}