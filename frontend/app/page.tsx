"use client";
import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ContextPrompt from "./components/ContextPrompt";
import FileUpload from "./components/FileUpload";

interface Message {
  role: "user" | "bot";
  text: string;
}

export default function Home() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [shinanContext, setShinanContext] = useState<{
    company: string;
    role: string;
    interests: string[];
  } | null>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "upload">("chat");
  const chatRef = useRef<HTMLDivElement>(null);
  const [agentStep, setAgentStep] = useState<string | null>(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages, loading]);

  // Handler to set context and send to backend
  const handleSetContext = async (context: { company: string; role: string; interests: string[] }) => {
    try {
      const res = await fetch("http://localhost:8000/client/context", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(context),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      setShinanContext(context);
    } catch (err: any) {
      setError("Failed to set context: " + (err.message || "Unknown error"));
    }
  };

  const sendMessage = async () => {
    if (!input.trim() || !shinanContext) return;
    setMessages((msgs) => [...msgs, { role: "user", text: input }]);
    setLoading(true);
    setError("");
    setAgentStep(null);
    const userInput = input;
    setInput("");
    // Show thank you message after 1 second
    setTimeout(() => {
      setMessages((msgs) => [
        ...msgs,
        { role: "bot", text: "Thank you for using me, hang on a bit! ご利用、ありがとうございます！少々お待ちください。" }
      ]);
    }, 1000);
    try {
      const res = await fetch("http://localhost:8000/client/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userInput }),
      });
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      setMessages((msgs) => [...msgs, { role: "bot", text: typeof data === "string" ? data : data.result || JSON.stringify(data) }]);
    } catch (err: any) {
      setMessages((msgs) => [...msgs, { role: "bot", text: "Error: Could not get response." }]);
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      width: "100vw",
      background: "#e6f9ed",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      position: "relative"
    }}>
      <AnimatePresence>
        {!shinanContext && (
          <ContextPrompt onSubmit={handleSetContext} />
        )}
      </AnimatePresence>
      {shinanContext && (
        <motion.div
          initial={{ opacity: 0, y: 40, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 40, scale: 0.95 }}
          transition={{ duration: 0.5, type: "spring", stiffness: 120 }}
          style={{
            background: "#f3fff6",
            borderRadius: 24,
            boxShadow: "0 8px 32px rgba(0,0,0,0.10)",
            width: 700,
            maxWidth: "98vw",
            minHeight: 700,
            padding: 0,
            display: "flex",
            flexDirection: "column",
            zIndex: 2
          }}
        >
          <div style={{ display: "flex", justifyContent: "center", gap: 0, borderBottom: "1px solid #b6e2c6", background: "#e6f9ed" }}>
            <button
              onClick={() => setActiveTab("chat")}
              style={{
                flex: 1,
                padding: "18px 0",
                fontWeight: 700,
                fontSize: 18,
                background: activeTab === "chat" ? "#f3fff6" : "#e6f9ed",
                border: "none",
                borderBottom: activeTab === "chat" ? "3px solid #3bb273" : "3px solid transparent",
                color: activeTab === "chat" ? "#1a3d2f" : "#3bb273",
                cursor: "pointer",
                borderTopLeftRadius: 16,
                borderTopRightRadius: 0,
                outline: "none",
                transition: "all 0.2s"
              }}
            >
              Chat
            </button>
            <button
              onClick={() => setActiveTab("upload")}
              style={{
                flex: 1,
                padding: "18px 0",
                fontWeight: 700,
                fontSize: 18,
                background: activeTab === "upload" ? "#f3fff6" : "#e6f9ed",
                border: "none",
                borderBottom: activeTab === "upload" ? "3px solid #3bb273" : "3px solid transparent",
                color: activeTab === "upload" ? "#1a3d2f" : "#3bb273",
                cursor: "pointer",
                borderTopLeftRadius: 0,
                borderTopRightRadius: 16,
                outline: "none",
                transition: "all 0.2s"
              }}
            >
              Upload
            </button>
          </div>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", background: "#f3fff6" }}>
            <AnimatePresence mode="wait">
              {activeTab === "chat" ? (
                <motion.div
                  key="chat"
                  initial={{ opacity: 0, x: 40 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -40 }}
                  transition={{ duration: 0.3 }}
                  style={{ flex: 1, display: "flex", flexDirection: "column", height: 0 }}
                >
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
                            background: msg.role === "user" ? "#3bb273" : "#e6f9ed",
                            color: msg.role === "user" ? "#fff" : "#1a3d2f",
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
                            background: "#b6e2c6",
                            color: "#1a3d2f",
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
                          style={{ alignSelf: "flex-start", color: "#3bb273", fontStyle: "italic" }}
                        >
                          Bot is typing...
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                  <form
                    onSubmit={e => {
                      e.preventDefault();
                      if (!loading) sendMessage();
                    }}
                    style={{
                      display: "flex",
                      gap: 12,
                      padding: 24,
                      borderTop: "1px solid #b6e2c6",
                      background: "#e6f9ed",
                      borderBottomLeftRadius: 24,
                      borderBottomRightRadius: 24,
                    }}
                  >
                    <input
                      type="text"
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      placeholder="Type your research question..."
                      style={{
                        flex: 1,
                        border: "1px solid #b6e2c6",
                        borderRadius: 10,
                        padding: "14px 16px",
                        fontSize: 17,
                        outline: "none",
                        background: "#fff",
                        color: "#1a3d2f"
                      }}
                      disabled={loading}
                      autoFocus
                    />
                    <button
                      type="submit"
                      disabled={loading || !input.trim()}
                      style={{
                        background: loading ? "#b6e2c6" : "#3bb273",
                        color: "#fff",
                        border: "none",
                        borderRadius: 10,
                        padding: "0 28px",
                        fontWeight: 700,
                        fontSize: 17,
                        cursor: loading ? "not-allowed" : "pointer",
                        transition: "background 0.2s"
                      }}
                    >
                      Send
                    </button>
                  </form>
                  {error && <div style={{ color: '#e74c3c', margin: 8, textAlign: 'center' }}>{error}</div>}
                </motion.div>
              ) : (
                <motion.div
                  key="upload"
                  initial={{ opacity: 0, x: -40 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 40 }}
                  transition={{ duration: 0.3 }}
                  style={{ flex: 1, display: "flex", flexDirection: "column", height: 0, padding: 36 }}
                >
                  <FileUpload />
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.div>
      )}
    </div>
  );
}
