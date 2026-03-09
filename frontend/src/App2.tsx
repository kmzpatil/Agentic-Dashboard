import React, { useState, useRef, useEffect } from 'react';

// --- Types & Interfaces ---
export interface Message {
  id: number;
  sender: 'bot' | 'user';
  text: string;
}

interface ChatSidebarProps {
  messages: Message[];
  onSendMessage: (text: string) => void;
  isLoading?: boolean;
}

interface XmlDashboardProps {
  xmlString: string;
}

// --- 1. Main Parent Component ---
export default function DashboardLayout() {
  // Updated XML State based on your image
  const [xmlData, setXmlData] = useState<string>(
`<dashboard>
  <aiSummary>
    This period saw a 12.4% increase in uploads driven primarily by Sports 1 and News Prime. However, publish conversion dropped to 61.5%, indicating a growing backlog in the review pipeline. Reels and Shorts continue to dominate output, representing 68% of all published content. Action needed: Kids Zone and Business 24 show critically low publish rates below 20%.
  </aiSummary>
  <keyMetrics>
    <metric title="Uploaded" value="12,847" trend="+12.4%" />
    <metric title="Processed" value="11,203" trend="+8.7%" />
    <metric title="Published" value="6,891" trend="-2.3%" />
    <metric title="Duration" value="4,231 hrs" trend="+15.1%" />
    <metric title="Conversion" value="61.5 %" trend="-4.1%" />
    <metric title="Channels" value="34" trend="+3%"   />
    
    <metric title="Users" value="127" trend="+9.2%" />
  </keyMetrics>
  <alerts>
    <alert title="Processed vs Published Gap" value="38%" description="Sports 1 has 2,340 processed videos but only 890 published (38% conversion)" />
    <alert title="Fastest Growing Output" value="+45%" description="Reels output grew 45% compared to last month, led by Entertainment HD" />
    <alert title="Low-Performing Channel" value="12%" description="Kids Zone has only 12% publish conversion rate, lowest across all channels" />
    <alert title="Missing Data Warning" value="170" description="127 videos missing team_name mapping, 43 missing platform data" />
  </alerts>
</dashboard>`
  );

  const [messages, setMessages] = useState<Message[]>([
    { id: 1, sender: 'bot', text: 'Dashboard loaded. Ask me to update any metric, add alerts, or change the summary.' }
  ]);
  const [isLoading, setIsLoading] = useState(false);

  const handleUserMessage = async (text: string) => {
    setMessages((prev) => [...prev, { id: Date.now(), sender: 'user', text }]);
    setIsLoading(true);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text, currentXml: xmlData }),
      });

      // Read as text first to avoid crashing on empty/non-JSON responses
      const rawText = await res.text();
      let data: any;
      try {
        data = JSON.parse(rawText);
      } catch {
        throw new Error(rawText || `Server returned status ${res.status} with no body. Is the backend running on port 3001?`);
      }

      if (!res.ok) {
        throw new Error(data.error || `Server error (${res.status})`);
      }

      // Update chat with AI reply
      setMessages((prev) => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: data.reply,
      }]);

      // Update XML dashboard state
      if (data.updatedXml) {
        setXmlData(data.updatedXml);
      }
    } catch (err: any) {
      setMessages((prev) => [...prev, {
        id: Date.now() + 1,
        sender: 'bot',
        text: `⚠ Error: ${err.message || 'Something went wrong. Is the backend running?'}`,
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen w-full bg-[#0b1114] font-sans overflow-hidden text-gray-200">
      <div className="w-1/3 min-w-[300px] border-r border-gray-800 bg-[#12181b] flex flex-col shadow-lg z-10">
        <ChatSidebar messages={messages} onSendMessage={handleUserMessage} isLoading={isLoading} />
      </div>
      <div className="w-2/3 flex flex-col bg-[#0b1114] overflow-auto p-8">
        <VisualDashboard xmlString={xmlData} />
      </div>
    </div>
  );
}

// --- 2. Left Component: Chat Sidebar (Adjusted for dark mode) ---
function ChatSidebar({ messages, onSendMessage, isLoading }: ChatSidebarProps) {
  const [input, setInput] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim()) return;
    onSendMessage(input);
    setInput('');
  };

  return (
    <>
      <div className="p-4 border-b border-gray-800 bg-[#12181b] flex items-center justify-between shadow-sm">
        <h2 className="font-semibold text-gray-200">AI Assistant</h2>
        <span className="flex h-3 w-3 relative">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-teal-400 opacity-75"></span>
          <span className="relative inline-flex rounded-full h-3 w-3 bg-teal-500"></span>
        </span>
      </div>
      <div className="flex-1 p-4 overflow-y-auto space-y-4">
        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] p-3 rounded-lg text-sm shadow-sm ${
                msg.sender === 'user' ? 'bg-teal-700 text-white rounded-br-none' : 'bg-[#1e262b] text-gray-300 border border-gray-700 rounded-bl-none'
              }`}>
              {msg.text}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-[#1e262b] text-gray-400 border border-gray-700 rounded-lg rounded-bl-none p-3 text-sm shadow-sm flex items-center gap-1.5">
              <span className="w-2 h-2 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
              <span className="w-2 h-2 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
              <span className="w-2 h-2 bg-teal-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="p-4 border-t border-gray-800 bg-[#12181b]">
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={isLoading ? 'Thinking...' : 'Type a command...'}
            disabled={isLoading}
            className="flex-1 px-4 py-2 bg-[#1e262b] border border-gray-700 text-white rounded-md focus:outline-none focus:ring-1 focus:ring-teal-500 disabled:opacity-50"
          />
          <button type="submit" className="px-4 py-2 bg-teal-600 text-white rounded-md hover:bg-teal-500 font-medium">
            Send
          </button>
        </form>
      </div>
    </>
  );
}

// --- 3. Right Component: Visual Dashboard (Rebuilt for new XML) ---
function VisualDashboard({ xmlString }: XmlDashboardProps) {
  const [aiSummary, setAiSummary] = useState<string>('');
  const [metrics, setMetrics] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);

  useEffect(() => {
    try {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(xmlString, "text/xml");

      // 1. Extract AI Summary
      const summaryNode = xmlDoc.querySelector("aiSummary");
      if (summaryNode) setAiSummary(summaryNode.textContent || '');

      // 2. Extract Key Metrics
      const metricNodes = xmlDoc.querySelectorAll("keyMetrics metric");
      setMetrics(Array.from(metricNodes).map(node => ({
        title: node.getAttribute("title") || "",
        value: node.getAttribute("value") || "",
        trend: node.getAttribute("trend") || ""
      })));

      // 3. Extract Alerts
      const alertNodes = xmlDoc.querySelectorAll("alerts alert");
      setAlerts(Array.from(alertNodes).map(node => ({
        title: node.getAttribute("title") || "",
        value: node.getAttribute("value") || "",
        description: node.getAttribute("description") || ""
      })));

    } catch (error) {
      console.error("Failed to parse XML", error);
    }
  }, [xmlString]);

  return (
    <div className="flex flex-col gap-8 w-full h-full max-w-6xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold text-white mb-1">Executive Summary</h1>
        <p className="text-gray-400 text-sm">High-level overview of media operations performance</p>
      </div>

      {/* AI Summary Block */}
      <div className="bg-[#151c21] border border-gray-800 rounded-xl p-5 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <div className="bg-teal-900/50 p-1.5 rounded-full">
             <span className="text-teal-400 text-xs font-bold">✧</span>
          </div>
          <h2 className="text-sm font-semibold text-gray-200">AI Summary</h2>
          <span className="ml-auto text-[10px] bg-gray-800 text-gray-400 px-2 py-1 rounded-full">Auto-generated</span>
        </div>
        <p className="text-sm text-gray-400 leading-relaxed">
          {aiSummary}
        </p>
      </div>

      {/* Key Metrics Row */}
      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Key Metrics <span className="text-gray-600 normal-case ml-1">vs. previous period</span></h3>
        <div className="flex flex-wrap gap-4">
          {metrics.map((metric, idx) => {
            const isPositive = metric.trend.startsWith('+');
            return (
              <div key={idx} className="bg-[#151c21] border border-gray-800 p-4 rounded-xl flex-1 min-w-[140px]">
                <div className="text-xs text-gray-400 mb-2">{metric.title}</div>
                <div className="text-2xl font-bold text-white mb-2">{metric.value}</div>
                <div className={`text-xs font-medium flex items-center gap-1 ${isPositive ? 'text-green-500' : 'text-red-500'}`}>
                  {isPositive ? '↗' : '↘'} {metric.trend}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Alerts & Signals Row */}
      <div>
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Alerts & Signals <span className="text-gray-600 normal-case ml-1">Items requiring attention</span></h3>
        <div className="grid grid-cols-4 gap-4">
          {alerts.map((alert, idx) => {
            // Very simple color logic based on the image's vibe
            let colorClass = "text-yellow-500";
            if (idx === 1) colorClass = "text-green-500";
            if (idx === 2) colorClass = "text-red-500";
            if (idx === 3) colorClass = "text-blue-500";

            return (
              <div key={idx} className="bg-[#151c21] border border-gray-800 p-5 rounded-xl flex flex-col justify-between">
                <div>
                  <div className={`text-sm font-semibold mb-2 flex items-center gap-2 ${colorClass}`}>
                    <span>⚠</span> {alert.title}
                  </div>
                  <p className="text-xs text-gray-500 leading-relaxed mb-4">
                    {alert.description}
                  </p>
                </div>
                <div className={`text-2xl font-bold ${colorClass}`}>
                  {alert.value}
                </div>
              </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}