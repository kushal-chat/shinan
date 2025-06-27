import React, { useState, useEffect } from "react";

interface ContextPromptProps {
  onSubmit: (context: { company: string; role: string; interests: string[] }) => void;
}

const ContextPrompt: React.FC<ContextPromptProps> = ({ onSubmit }) => {
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [interests, setInterests] = useState("");
  const [show, setShow] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    setShow(true);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!company.trim() || !role.trim() || !interests.trim()) {
      setError("Please fill in all fields.");
      return;
    }
    setError("");
    setShow(false);
    onSubmit({
      company: company.trim(),
      role: role.trim(),
      interests: interests.split(",").map(i => i.trim()).filter(Boolean),
    });
  };

  if (!show) return null;

  return (
    <div style={{
      position: "fixed",
      top: 0,
      left: 0,
      width: "100vw",
      height: "100vh",
      background: "rgba(0,0,0,0.45)",
      zIndex: 1000,
      display: "flex",
      alignItems: "center",
      justifyContent: "center"
    }}>
      <form
        onSubmit={handleSubmit}
        style={{
          background: "#fff",
          borderRadius: 12,
          boxShadow: "0 4px 24px rgba(0,0,0,0.18)",
          padding: 32,
          minWidth: 340,
          display: "flex",
          flexDirection: "column",
          gap: 16,
          alignItems: "center"
        }}
      >
        <div style={{ fontSize: 22, fontWeight: 700, marginBottom: 8 }}>Provide Context</div>
        <input
          value={company}
          onChange={e => setCompany(e.target.value)}
          placeholder="Company"
          style={{ width: 260, borderRadius: 8, border: "1px solid #e5e7eb", padding: 10, fontSize: 15 }}
          autoFocus
        />
        <input
          value={role}
          onChange={e => setRole(e.target.value)}
          placeholder="Role"
          style={{ width: 260, borderRadius: 8, border: "1px solid #e5e7eb", padding: 10, fontSize: 15 }}
        />
        <input
          value={interests}
          onChange={e => setInterests(e.target.value)}
          placeholder="Interests (comma separated)"
          style={{ width: 260, borderRadius: 8, border: "1px solid #e5e7eb", padding: 10, fontSize: 15 }}
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
          Submit
        </button>
      </form>
    </div>
  );
};

export default ContextPrompt; 