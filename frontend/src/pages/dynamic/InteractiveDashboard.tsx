import React, { useState, useRef, useEffect } from "react";
import { useDashboardAgent } from "../../helpers/useDashboardAgent";

// Import our new modular UI components
import AgentPanel from "../../components/dashboard/AgentPanel";
import DashboardCanvas from "../../components/dashboard/DashboardCanvas";

export default function InteractiveDashboard() {
  const { 
    xml, setXml, history, msgs, status, notice, setNotice, send, undo, cfg, wCount 
  } = useDashboardAgent();

  const [input, setInput] = useState<string>("");
  const [rightTab, setRightTab] = useState<string>("chat");

  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs]);

  const handleSend = () => {
    send(input);
    setInput("");
  };

  return (
    <div style={{ display: "flex", height: "100%" }}>
      <AgentPanel 
        rightTab={rightTab}
        setRightTab={setRightTab}
        input={input}
        setInput={setInput}
        handleSend={handleSend}
        msgs={msgs}
        status={status}
        endRef={endRef}
        inputRef={inputRef}
        xml={xml}
        setXml={setXml}
        undo={undo}
        historyLength={history.length}
      />

      <DashboardCanvas 
        notice={notice}
        setNotice={setNotice}
        cfg={cfg}
        wCount={wCount}
        xml={xml}
      />
    </div>
  );
}