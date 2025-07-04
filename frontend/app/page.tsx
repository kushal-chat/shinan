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

export default function Home() {
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
                  <Chat shinanContext={shinanContext} />
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