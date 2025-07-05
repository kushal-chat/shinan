"use client";
import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Toaster, toast } from 'sonner'
import FileUpload from "./FileUpload";

interface Message {
  role: "user" | "bot";
  text: string;
}

interface ChatProps {
  shinanContext: {
    company: string;
    role: string;
    interests: string[];
  } | null;
}

const Chat: React.FC<ChatProps> = ({ shinanContext }) => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [agentStep, setAgentStep] = useState<string | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const sendMessage = async () => {
    if (!input.trim() || !shinanContext) return;
  
    // Add user's message
    setMessages((msgs) => [...msgs, { role: "user", text: input }]);
    setLoading(true);
    setError("");
    setAgentStep(null);
    const userInput = input;
    setInput("");
  
    // Toast feedback
    setTimeout(() => {
      toast("Thank you for using me!");
    }, 100);
  
    try {
  
      const res = await fetch("http://localhost:8000/client/deep_research", {
        method: "POST",
        headers: { "Content-Type": "application/json"}, // "Accepts": "text/event-stream" 
        body: JSON.stringify({ query: userInput }),
      });
  
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      if (!res.body) throw new Error("No response body");
  
      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let fullText = "";
  
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
  
        const chunk = decoder.decode(value, { stream: true });
        setMessages((msgs) => [...msgs, { role: "bot", text: chunk }]);
      }
    } catch (err: any) {
      setMessages((msgs) => [...msgs, { role: "bot", text: "Error: Could not get response." }]);
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };  

  if (!shinanContext) return null;

  return (
    <motion.div
      key="chat"
      initial={{ opacity: 0, x: 40 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: -40 }}
      transition={{ duration: 0.3 }}
      style={{ flex: 1, display: "flex", flexDirection: "column", height: 0 }}
    >
      <Toaster />
      {/* Chat container */}
      <div
        ref={chatRef}
        style={{
          flex: 1,
          overflowY: "auto",
          padding: 36,
          display: "flex",
          flexDirection: "column",
          gap: 18,
          minHeight: 400,
        }}
      >
        {/* Messages */}
        <AnimatePresence>
          {messages.map((msg, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              transition={{ duration: 0.2 }}
              style={{
                alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
                maxWidth: "80%",
                background: msg.role === "user" ? "#757575" : "#f5f5f7",
                color: msg.role === "user" ? "#fff" : "#232323",
                borderRadius: 14,
                padding: "14px 20px",
                fontSize: 17,
                boxShadow: msg.role === "user" ? "0 2px 8px rgba(59,178,115,0.08)" : "none",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {msg.text}
            </motion.div>
          ))}
          {agentStep && (
            <motion.div
              key="agent-step"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 10 }}
              transition={{ duration: 0.2 }}
              style={{
                alignSelf: "flex-start",
                maxWidth: "80%",
                background: "#bdbdbd",
                color: "#232323",
                borderRadius: 14,
                padding: "14px 20px",
                fontSize: 17,
                fontStyle: "italic",
                marginTop: 4,
                marginBottom: 4,
                boxShadow: "0 2px 8px rgba(59,178,115,0.08)",
              }}
            >
              {agentStep}
            </motion.div>
          )}
          {loading && !agentStep && (
            <motion.div
              key="loading"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              style={{ alignSelf: "flex-start", color: "#757575", fontStyle: "italic" }}
            >
              Bot is typing...
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Input and Send button */}
      <form
        onSubmit={e => {
          e.preventDefault();
          if (!loading) sendMessage();
        }}
        style={{
          display: "flex",
          gap: 12,
          padding: 24,
          borderTop: "1px solid #bdbdbd",
          background: "#ededed",
          borderBottomLeftRadius: 24,
          borderBottomRightRadius: 24,
        }}
      >
        {/* Input */}
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Type your research question..."
          style={{
            flex: 1,
            border: "1px solid #bdbdbd",
            borderRadius: 20,
            padding: "14px 16px",
            fontSize: 17,
            outline: "none",
            background: "#fff",
            color: "#232323"
          }}
          disabled={loading}
          autoFocus
        />

        <FileUpload />

        {/* Send button */}
        <motion.button
          type="submit"
          disabled={loading || !input.trim()}
          variants={{
            idle: {
              backgroundColor: "#757575",
              scale: 1,
              boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
              transition: { duration: 0.3 },
            },
            loading: {
              backgroundColor: "#bdbdbd",
              scale: 1.05,
              boxShadow: "0 4px 12px rgba(189,189,189,0.3)",
              transition: {
                repeat: Infinity,
                repeatType: "mirror" as const,
                duration: 1.1,
                backgroundColor: { duration: 0.25 },
                boxShadow: { duration: 0.25 },
                scale: { duration: 0.4 },
              },
            },
          }}
          animate={loading ? "loading" : "idle"}
          style={{
            color: "#fff",
            border: "none",
            borderRadius: 10,
            padding: "14px 16px",
            fontWeight: 700,
            fontSize: 17,
            cursor: loading ? "not-allowed" : "pointer",
            transition: "background 0.2s"
          }}
        >
          {loading ? (
            <span style={{ display: "inline-flex", alignItems: "center" }}>
              <span
                style={{
                  display: "inline-block",
                  verticalAlign: "middle",
                  marginRight: 8,
                  width: 18,
                  height: 18,
                }}
              >
                <svg
                  style={{
                    animation: "spin 1s linear infinite",
                    display: "block",
                  }}
                  width="18"
                  height="18"
                  viewBox="0 0 18 18"
                >
                  <circle
                    cx="9"
                    cy="9"
                    r="7"
                    fill="none"
                    stroke="#fff"
                    strokeWidth="2.5"
                    strokeDasharray="34"
                    strokeDashoffset="10"
                    strokeLinecap="round"
                    opacity="0.7"
                  />
                </svg>
                <style>
                  {`
                    @keyframes spin {
                      100% { transform: rotate(360deg); }
                    }
                  `}
                </style>
              </span>
              Sending...
            </span>
          ) : (
            "Send"
          )}
        </motion.button>
      </form>

      {/* Error */}
      {error && <div style={{ color: "#e74c3c", margin: 8, textAlign: "center" }}>{error}</div>}
    </motion.div>
  );
};

export default Chat; 