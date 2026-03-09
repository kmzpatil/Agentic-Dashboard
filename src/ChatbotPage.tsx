import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

type Message = {
  role: "user" | "assistant";
  content: string;
};

function ChatbotPage() {
  const navigate = useNavigate();
  const [messages, setMessages] = useState<Message[]>([
    { role: "assistant", content: "Hello! I am your AI assistant. Ask me anything." }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const newMessages: Message[] = [...messages, { role: "user", content: text }];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ message: text })
      });

      const data = await res.json();

      setMessages([
        ...newMessages,
        { role: "assistant", content: data.reply || "No response from server." }
      ]);
    } catch (error) {
      setMessages([
        ...newMessages,
        { role: "assistant", content: "Error connecting to backend." }
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#050505",
        color: "#fff",
        display: "flex",
        flexDirection: "column",
        fontFamily: "Inter, sans-serif"
      }}
    >
      <div
        style={{
          padding: "20px 24px",
          borderBottom: "1px solid #262626",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center"
        }}
      >
        <div>
          <h1 style={{ margin: 0, fontSize: 28 }}>AI Chatbot</h1>
          <p style={{ margin: "6px 0 0 0", color: "#a3a3a3" }}>
            Dedicated assistant workspace
          </p>
        </div>

        <button
          onClick={() => navigate("/")}
          style={{
            background: "#e00000",
            color: "#fff",
            border: "none",
            padding: "10px 16px",
            borderRadius: 6,
            cursor: "pointer",
            fontWeight: 600
          }}
        >
          Back to Dashboard
        </button>
      </div>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "24px",
          display: "flex",
          flexDirection: "column",
          gap: "14px"
        }}
      >
        {messages.map((msg, index) => (
          <div
            key={index}
            style={{
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "70%",
              padding: "12px 16px",
              borderRadius: 10,
              background: msg.role === "user" ? "#e00000" : "#111111",
              border: msg.role === "user" ? "none" : "1px solid #262626",
              color: "#fff",
              lineHeight: 1.5
            }}
          >
            {msg.content}
          </div>
        ))}

        {loading && (
          <div
            style={{
              alignSelf: "flex-start",
              background: "#111111",
              border: "1px solid #262626",
              padding: "12px 16px",
              borderRadius: 10,
              color: "#a3a3a3"
            }}
          >
            Thinking...
          </div>
        )}
      </div>

      <div
        style={{
          padding: "16px 24px",
          borderTop: "1px solid #262626",
          display: "flex",
          gap: 12
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          placeholder="Type your message..."
          style={{
            flex: 1,
            padding: "14px",
            background: "#111111",
            border: "1px solid #262626",
            borderRadius: 8,
            color: "#fff",
            outline: "none",
            fontSize: 14
          }}
        />

        <button
          onClick={sendMessage}
          disabled={loading}
          style={{
            background: loading ? "#444" : "#e00000",
            color: "#fff",
            border: "none",
            padding: "0 20px",
            borderRadius: 8,
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: 600
          }}
        >
          Send
        </button>
      </div>
    </div>
  );
}

export default ChatbotPage;