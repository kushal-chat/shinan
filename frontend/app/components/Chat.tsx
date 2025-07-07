"use client";
import React, { useState, useRef, useEffect } from "react";
import ReactMarkdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { motion, AnimatePresence, m } from "framer-motion";
import { Toaster, toast } from 'sonner'
import FileUpload from "./FileUpload";

interface Message {
  role: "user" | "bot" | "update";
  text: string;
}

interface Query {
  type: "bubble" | "streamingBubble" | "updates";
  text: string;
}

interface ChatProps {
  shinanContext: {
    company: string;
    role: string;
    interests: string[];
  } | null;
  mode?: "old" | "new";
  // potentially add more modes.
}

const Chat: React.FC<ChatProps> = ({ shinanContext, mode = "new" }) => {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [agentStep, setAgentStep] = useState<string | null>(null);
  const [agentUpdate, setAgentUpdate] = useState<string | null>(null);
  const chatRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const sendMessage = async () => {
    if (!input.trim() || !shinanContext) return;

    // Using Toast, may delete.
    if (!messages) {
      setTimeout(() => {
        toast("Thank you for using me!");
      }, 100);
    }
  
    // Add user's message
    setMessages((msgs) => [...msgs, { role: "user", text: input }]);
    setLoading(true);
    setError("");
    setAgentStep(null);
    const userInput = input;
    setInput("");
  
    try {
      const endpoint =
        mode === "old"
          ? "http://localhost:8000/client/query"
          : "http://localhost:8000/client/deep_research";

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: userInput }),
      });
  
      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      if (!res.body) throw new Error("No response body");
      
      const reader = res.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let streaming = false;
      let streamingMsgIndex: number;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
  
        const chunk = decoder.decode(value, { stream: true });

        if (chunk.startsWith("UPDATE " )) {
          streaming = false;
          const update_message = chunk.slice(7);
          setMessages((msgs) => [...msgs, { role: "update", text: update_message}]);
        } 

        else if (chunk.startsWith("STREAMING ")) {
          const stream_initial = chunk.slice(10);
          streaming = true;
      
          setMessages((msgs) => [...msgs, { role: "bot", text: ""}]);
        }

        else if (streaming) {
          setMessages((msgs) => {
            const updated = [...msgs]; 
            const lastIndex = updated.length - 1;
          
            updated[lastIndex] = {
              ...updated[lastIndex],
              text: updated[lastIndex].text + chunk,
            };
            return updated;
          });
        }

        else {
          streaming = false;
          setMessages((msgs) => [...msgs, { role: "bot", text: chunk }]);
        }
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
          {messages.map((msg, i) => {      

            // Message if user.
            if (msg.role === "user") {
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{ duration: 0.2 }}
                  style={{              
                    maxWidth: "80%",
                    borderRadius: 10,
                    padding: "12px 14px",
                    fontSize: 16,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    alignSelf: "flex-end",
                    background: "#757575",
                    color: "#fff",
                    boxShadow: "0 2px 8px rgba(59,178,115,0.08)",
                  }}
                >
                  {msg.text.startsWith("data:image/") ? (
                    <img
                      src={msg.text}
                      alt="uploaded"
                      style={{ maxWidth: "100%", borderRadius: 8 }}
                    />
                  ) : (
                    msg.text
                  )}
                </motion.div>
              );
            }

            // Message if bot.
            if (msg.role === "bot") {
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: 10 }}
                  transition={{ duration: 0.2 }}
                  style={{              
                    maxWidth: "80%",
                    borderRadius: 10,
                    padding: "8px 10px",
                    fontSize: 16,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-word",
                    alignSelf: "flex-start",
                    background: "#f5f5f7",
                    color: "#232323",
                  }}
                  dangerouslySetInnerHTML={{ __html: msg.text }}
                />
              );
            }

            // Update if update.
            if (msg.role === "update") {
              return (
                <motion.div
                  key={i}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  style={{              
                    alignSelf: "flex-start", 
                    color: "#757575", 
                    fontStyle: "italic"
                  }}
                >
                  {msg.text}
                </motion.div>
              );
            }
          })}
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

        {/* <div style={{ width: '100%', marginBottom: 6, zIndex: 2, position: 'relative', color: '#555', fontSize: 14 }}>
          {shinanContext && (
            <span>
              Your context: <b>Company:</b> {shinanContext.company}, <b>Role:</b> {shinanContext.role}, <b>Interests:</b> {shinanContext.interests.join(', ')}
            </span>
          )}
        </div> 
        <div> */}

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

        <FileUpload onResult={(result: string) => {
          let parsed: any;
          try { parsed = JSON.parse(result); } catch { parsed = null; }
          if (parsed && Array.isArray(parsed)) {
            parsed.forEach((msg: any) => {
              if (msg.content) {
                msg.content.forEach((item: any) => {
                  if (item.type === 'input_text') {
                    setMessages((msgs) => [...msgs, { role: 'bot', text: item.text }]);
                  } else if (item.type === 'input_image' && item.image_url) {
                    setMessages((msgs) => [...msgs, { role: 'bot', text: item.image_url }]);
                  }
                });
              }
            });
          } else {
            setMessages((msgs) => [...msgs, { role: 'bot', text: result }]);
          }
        }} />

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
      {error && <div style={{ color: "#e74c3c", margin: 8, textAlign: "center" }}>{error}</div>}
    </motion.div>
  );
};

export default Chat; 