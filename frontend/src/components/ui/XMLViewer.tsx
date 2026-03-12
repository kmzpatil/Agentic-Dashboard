import React from "react";
import { T } from "../../utils/theme";

export default function XMLViewer({ xml }: { xml: string }) {
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