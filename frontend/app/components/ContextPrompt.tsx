import React, { useState, useEffect } from "react";
import { Toaster, toast } from "sonner";
import { motion, AnimatePresence } from "framer-motion";

interface ContextPromptProps {
  onSubmit: (context: { company: string; role: string; interests: string[] }) => void;
}

const ContextPrompt: React.FC<ContextPromptProps> = ({ onSubmit }) => {
  const [user_id, setUserID] = useState("")
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [interests, setInterests] = useState("");
  const [show, setShow] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setShow(true);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!company.trim() || !role.trim() || !interests.trim()) {
      setError("全ての科目を入力してください。");
      return;
    }
    setError("");
    toast(
      `適切にお答えいたします。`,
      { duration: 1300 }
    );
    setTimeout(() => {
      onSubmit({
        company: company.trim(),
        role: role.trim(),
        interests: interests.split(",").map(i => i.trim()).filter(Boolean),
      });
    }, 1500)
  };

  if (!show) return null;

  return (
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      width: "100vw",
      height: "100vh",
      zIndex: 1000,
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }}>
      <Toaster />
      <AnimatePresence>
        {show && (
          <motion.form
            initial={{ opacity: 1, scale: 1}}
            whileHover={{ opacity: 1, scale: 1.01 }}
            transition={{ duration: 0.25 }}
            onSubmit={handleSubmit}
            style={{
              background: "#fff",
              borderRadius: 12,
              boxShadow: "4px 4px 4px rgba(0,0,0)",
              border: "1.54px solid black",
              padding: 32,
              minWidth: 500,
              display: "flex",
              flexDirection: "column",
              gap: 16,
              alignItems: "center",
              color: "#232323"
            }}
          >
            <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 8, color: "#232323" }}>ご職業などを入力してください。</div>
            <label style={{ color: "#232323", fontSize: 20, fontWeight: 600 }}>企業</label>
            <input
              value={company}
              onChange={e => setCompany(e.target.value)}
              placeholder="例：ソフトバンク"
              style={{ width: 260, borderRadius: 8, border: "1px solid #e5e7eb", padding: 10, fontSize: 15, color: "#232323" }}
              autoFocus
            />
            <label style={{ color: "#232323", fontSize: 20, fontWeight: 600 }}>職業</label>
            <input
              value={role}
              onChange={e => setRole(e.target.value)}
              placeholder="例：インターン"
              style={{ width: 260, borderRadius: 8, border: "1px solid #e5e7eb", padding: 10, fontSize: 15, color: "#232323" }}
            />
            <label style={{ color: "#232323", fontSize: 20, fontWeight: 600 }}>興味</label>
            <input
              value={interests}
              onChange={e => setInterests(e.target.value)}
              placeholder="例：AI、戦略"
              style={{ width: 260, borderRadius: 8, border: "1px solid #e5e7eb", padding: 10, fontSize: 15, color: "#232323" }}
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
                cursor: "pointer"
              }}
            >
              入力
            </button>
          </motion.form>
        )}
      </AnimatePresence>
    </div>
  );
};

export default ContextPrompt; 