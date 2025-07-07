"use client";
import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ContextPrompt from "./components/ContextPrompt";
import FileUpload from "./components/FileUpload";
import Chat from "./components/Chat";

interface Message {
  role: "user" | "bot";
  text: string;
}

function SettingsModal({
  open,
  onClose,
  chatMode,
  setChatMode,
  context,
  onUpdateContext,
}: {
  open: boolean;
  onClose: () => void;
  chatMode: "old" | "new";
  setChatMode: (mode: "old" | "new") => void;
  context: { company: string; role: string; interests: string[] } | null;
  onUpdateContext: (context: { company: string; role: string; interests: string[] }) => void;
}) {
  const [company, setCompany] = useState(context?.company || "");
  const [role, setRole] = useState(context?.role || "");
  const [interests, setInterests] = useState(context?.interests?.join(", ") || "");
  const [error, setError] = useState("");

  useEffect(() => {
    setCompany(context?.company || "");
    setRole(context?.role || "");
    setInterests(context?.interests?.join(", ") || "");
  }, [context, open]);

  if (!open) return null;
  return (
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      width: "100vw",
      height: "100vh",
      zIndex: 2000,
      background: "rgba(0,0,0,0.18)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }}>
      <div style={{
        background: "#fff",
        borderRadius: 12,
        boxShadow: "0 4px 24px rgba(0,0,0,0.18)",
        padding: 32,
        minWidth: 340,
        display: "flex",
        flexDirection: "column",
        gap: 18,
        alignItems: "center",
        color: "#232323",
        position: "relative"
      }}>
        <button onClick={onClose} style={{ position: "absolute", top: 12, right: 12, background: "none", border: "none", fontSize: 22, cursor: "pointer" }}>&times;</button>
        <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Settings</div>
        <div style={{ width: "100%", marginBottom: 8 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Chat Mode</div>
          <label style={{ marginRight: 16 }}>
            <input
              type="radio"
              checked={chatMode === "old"}
              onChange={() => setChatMode("old")}
              style={{ marginRight: 4 }}
            />
            Deterministic
          </label>
          <label>
            <input
              type="radio"
              checked={chatMode === "new"}
              onChange={() => setChatMode("new")}
              style={{ marginRight: 4 }}
            />
            Handoffs
          </label>
        </div>
        <form
          onSubmit={e => {
            e.preventDefault();
            if (!company.trim() || !role.trim() || !interests.trim()) {
              setError("Please fill in all fields.");
              return;
            }
            setError("");
            onUpdateContext({
              company: company.trim(),
              role: role.trim(),
              interests: interests.split(",").map(i => i.trim()).filter(Boolean),
            });
            onClose();
          }}
          style={{ width: "100%", display: "flex", flexDirection: "column", gap: 10 }}
        >
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Current Context</div>
          <label style={{ alignSelf: "flex-start", color: "#232323", fontSize: 15, fontWeight: 500 }}>Company</label>
          <input
            value={company}
            onChange={e => setCompany(e.target.value)}
            placeholder="Company"
            style={{ width: "100%", borderRadius: 8, border: "1px solid #e5e7eb", padding: 10, fontSize: 15, color: "#232323" }}
          />
          <label style={{ alignSelf: "flex-start", color: "#232323", fontSize: 15, fontWeight: 500 }}>Role</label>
          <input
            value={role}
            onChange={e => setRole(e.target.value)}
            placeholder="Role"
            style={{ width: "100%", borderRadius: 8, border: "1px solid #e5e7eb", padding: 10, fontSize: 15, color: "#232323" }}
          />
          <label style={{ alignSelf: "flex-start", color: "#232323", fontSize: 15, fontWeight: 500 }}>Interests (comma separated)</label>
          <input
            value={interests}
            onChange={e => setInterests(e.target.value)}
            placeholder="Interests (comma separated)"
            style={{ width: "100%", borderRadius: 8, border: "1px solid #e5e7eb", padding: 10, fontSize: 15, color: "#232323" }}
          />
          {error && <div style={{ color: "red", fontSize: 14 }}>{error}</div>}
          <button
            type="submit"
            style={{
              background: "#2563eb",
              color: "#fff",
              border: "none",
              borderRadius: 8,
              padding: "8px 24px",
              fontWeight: 600,
              fontSize: 15,
              cursor: "pointer",
              marginTop: 8
            }}
          >
            Update Context
          </button>
        </form>
      </div>
    </div>
  );
}

export default function Home() {
  const [shinanContext, setShinanContext] = useState<{
    company: string;
    role: string;
    interests: string[];
  } | null>(null);
  const [activeTab, setActiveTab] = useState<"chat" | "upload">("chat");
  const chatRef = useRef<HTMLDivElement>(null);
  const [agentStep, setAgentStep] = useState<string | null>(null);
  const [chatMode, setChatMode] = useState<"old" | "new">("old");
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop = chatRef.current.scrollHeight;
    }
  }, [agentStep]);

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
      throw new Error(`Was unable to set the context.`)
    }
  };

  return (
    <div style={{
      height: "100vh",
      width: "100vw",
      background: "#7CAE7A",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      position: "relative"
    }}>
      {/* Settings Button */}
      <button
        onClick={() => setSettingsOpen(true)}
        style={{ position: "absolute", top: 24, right: 24, zIndex: 200, background: "#fff", border: "none", borderRadius: "50%", width: 44, height: 44, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 2px 8px rgba(0,0,0,0.08)", cursor: "pointer", fontSize: 24 }}
        aria-label="Settings"
      >
        <span role="img" aria-label="settings">⚙️</span>
      </button>
      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        chatMode={chatMode}
        setChatMode={setChatMode}
        context={shinanContext}
        onUpdateContext={handleSetContext}
      />
      {/* Context Prompt */}
      <AnimatePresence>
        {!shinanContext && (
          <ContextPrompt onSubmit={handleSetContext} />
        )}
      </AnimatePresence>

      {/* Chatbot Container */}
      {shinanContext && (
        <div className="chatbot-container" style={{ overflow: "hidden" }}>
          <motion.div
            initial={{ boxShadow: "0px 0px #000" }}
            animate={{ boxShadow: "10px 10px #000" }}
            exit={{ opacity: 0, y: 40, scale: 0.95 }}
            transition={{ duration: 0.5, type: "spring", stiffness: 120 }}
            style={{
              width: "90vw",
              height: "75vh",
              display: "flex",
              background: "#ededed",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                background: "#ededed",
                overflowY: "auto",
                minHeight: 0,
                maxHeight: "100%",
              }}
            >
              <AnimatePresence mode="wait">
                {activeTab === "chat" ? (
                  <Chat shinanContext={shinanContext} mode={chatMode} />
                ) : (
                  <motion.div
                    key="upload"
                    initial={{ opacity: 0, x: -40 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: 40 }}
                    transition={{ duration: 0.3 }}
                    style={{
                      flex: 1,
                      display: "flex",
                      flexDirection: "column",
                      height: "100%",
                      width: "100%",
                      padding: 0,
                      overflowY: "auto",
                      minHeight: 0,
                    }}
                  >
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </motion.div>
        </div>
      )}
    </div>
  );
}