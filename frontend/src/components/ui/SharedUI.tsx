import React from "react";
import { T } from "../../utils/theme";
import type{ CardProps } from "../../store";

export function Card({ children, style = {} }: CardProps) {
  return (
    <div style={{ background: T.surface, border: `1px solid ${T.border}`, borderRadius: 8, padding: "20px", height: "100%", ...style }}>
      {children}
    </div>
  );
}

export function WHead({ title }: { title: string }) {
  return (
    <div style={{ fontSize: 13, fontWeight: 600, color: T.text, marginBottom: 16, textTransform: "uppercase", letterSpacing: "0.05em" }}>
      {title}
    </div>
  );
}

export const RTip = ({ active, payload, label }: any) => {
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

export function ErrW({ msg }: { msg: string }) {
  return (
    <div style={{ background: "#1a0505", border: `1px solid ${T.danger}`, borderRadius: 8, padding: "20px", height: "100%", display: "flex", alignItems: "center", gap: 8 }}>
      <span style={{ color: T.danger }}>⚠</span>
      <span style={{ fontSize: 12, color: T.danger }}>{msg}</span>
    </div>
  );
}