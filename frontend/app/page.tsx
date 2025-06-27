"use client";
import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const blue = "#2563eb";
const lightGray = "#f7f8fa";
const borderGray = "#e5e7eb";

const waveVariants = {
  animate: {
    y: [0, 10, 0],
    transition: {
      duration: 8,
      repeat: Infinity,
      ease: "easeInOut" as const
    }
  }
};

const guideVariants = {
  initial: { opacity: 0, y: 20 },
  animate: {
    opacity: 0.7,
    y: 0,
    transition: { duration: 1.2, ease: "easeInOut" as const }
  }
};

const cardVariants = {
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.7, ease: "easeInOut" as const } }
};

const headingUnderline = {
  initial: { scaleX: 0 },
  animate: { scaleX: 1, transition: { duration: 0.7, delay: 0.3, ease: "easeInOut" as const } }
};

const formStagger = {
  animate: {
    transition: {
      staggerChildren: 0.13,
      delayChildren: 0.5
    }
  }
};

const formFieldVariants = {
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.5, ease: "easeInOut" as const } }
};

const resultVariants = {
  initial: { opacity: 0, scale: 0.98 },
  animate: { opacity: 1, scale: 1, transition: { duration: 0.5, ease: "easeInOut" as const } },
  exit: { opacity: 0, scale: 0.98, transition: { duration: 0.3 } }
};

export default function Home() {
  const [query, setQuery] = useState("");
  const [context, setContext] = useState("");
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);
    setError("");

    let contextObj = undefined;
    if (context.trim()) {
      try {
        contextObj = JSON.parse(context);
      } catch {
        setError("Context must be valid JSON");
        setLoading(false);
        return;
      }
    }

    try {
      const res = await fetch("http://localhost:8000/client/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, context: contextObj }),
      });
      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }
      const data = await res.text();
      setResult(data);
    } catch (err: any) {
      setError(err.message || "Unknown error");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: "100vh",
      width: "100vw",
      overflow: "hidden",
      position: "relative",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: lightGray
    }}>
      {/* Subtle ocean wave background */}
      <motion.svg
        style={{ position: "absolute", bottom: 0, left: 0, width: "100%", zIndex: 0, opacity: 0.13 }}
        viewBox="0 0 1440 320"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        height="320"
        variants={waveVariants}
        animate="animate"
      >
        <path
          fill={blue}
          fillOpacity="0.5"
          d="M0,224L48,202.7C96,181,192,139,288,128C384,117,480,139,576,154.7C672,171,768,181,864,186.7C960,192,1056,192,1152,186.7C1248,181,1344,171,1392,165.3L1440,160L1440,320L1392,320C1344,320,1248,320,1152,320C1056,320,960,320,864,320C768,320,672,320,576,320C480,320,384,320,288,320C192,320,96,320,48,320L0,320Z"
        />
      </motion.svg>
      {/* Shinan overlay */}
      <motion.div
        variants={guideVariants}
        initial="initial"
        animate="animate"
        style={{
          position: "absolute",
          top: 36,
          left: 0,
          width: "100%",
          textAlign: "center",
          zIndex: 2,
          fontSize: 48,
          fontWeight: 500,
          color: blue,
          letterSpacing: 6,
          fontFamily: "'Noto Sans JP', 'Noto Sans SC', 'Microsoft YaHei', sans-serif",
          userSelect: "none",
          opacity: 0.7
        }}
      >
        Shinan
      </motion.div>
      <motion.main
        variants={cardVariants}
        initial="initial"
        animate="animate"
        style={{
          background: "#fff",
          borderRadius: 14,
          border: `1px solid ${borderGray}`,
          boxShadow: "none",
          padding: 36,
          width: 420,
          maxWidth: "92vw",
          zIndex: 3,
          display: "flex",
          flexDirection: "column",
          alignItems: "center"
        }}
      >
        <div style={{ width: "100%", textAlign: "center", marginBottom: 24 }}>
          <h1 style={{ fontSize: 24, fontWeight: 600, letterSpacing: 1, color: "#222", marginBottom: 0, fontFamily: "'Noto Sans JP', 'Noto Sans SC', 'Microsoft YaHei', sans-serif" }}>
            Shinan Query Client
          </h1>
          <motion.div
            variants={headingUnderline}
            initial="initial"
            animate="animate"
            style={{
              height: 2,
              width: 48,
              background: blue,
              margin: "10px auto 0 auto",
              borderRadius: 2,
              transformOrigin: "left center"
            }}
          />
        </div>
        <motion.form
          onSubmit={handleSubmit}
          style={{ width: "100%", display: "flex", flexDirection: "column", gap: 18 }}
          variants={formStagger}
          initial="initial"
          animate="animate"
        >
          <motion.div style={{ display: "flex", flexDirection: "column", gap: 6 }} variants={formFieldVariants}>
            <label style={{ fontWeight: 400, color: "#222", fontSize: 15, marginBottom: 2 }}>Query</label>
            <input
              type="text"
              value={query}
              onChange={e => setQuery(e.target.value)}
              style={{ padding: 8, border: `1px solid ${borderGray}`, borderRadius: 6, background: "#fafbfc", fontSize: 15 }}
              placeholder="e.g. What is the Rotten Tomatoes rating of The Incredibles?"
              required
            />
          </motion.div>
          <motion.div style={{ display: "flex", flexDirection: "column", gap: 6 }} variants={formFieldVariants}>
            <label style={{ fontWeight: 400, color: "#222", fontSize: 15, marginBottom: 2 }}>Context (JSON, optional)</label>
            <textarea
              value={context}
              onChange={e => setContext(e.target.value)}
              rows={3}
              style={{ width: '100%', marginBottom: 12, padding: 8, border: `1px solid ${borderGray}`, borderRadius: 6, background: "#fafbfc", fontSize: 15 }}
              placeholder='e.g. {"user_id": "123"}'
            />
          </motion.div>
          <motion.button
            type="submit"
            disabled={loading}
            whileHover={{ scale: loading ? 1 : 1.03 }}
            whileTap={{ scale: loading ? 1 : 0.98 }}
            style={{
              background: blue,
              color: "#fff",
              border: "none",
              borderRadius: 6,
              padding: "12px 0",
              fontWeight: 500,
              fontSize: 16,
              cursor: loading ? "not-allowed" : "pointer",
              boxShadow: "none",
              transition: "background 0.2s",
              marginTop: 6
            }}
            variants={formFieldVariants}
          >
            {loading ? "Submitting..." : "Submit"}
          </motion.button>
        </motion.form>
        {error && <div style={{ color: 'red', marginTop: 16 }}>{error}</div>}
        <AnimatePresence>
          {result && (
            <motion.div
              key="result"
              variants={resultVariants}
              initial="initial"
              animate="animate"
              exit="exit"
              style={{ marginTop: 28, width: "100%" }}
            >
              <pre style={{ background: "#f8fafc", padding: 18, borderRadius: 8, fontSize: 14, color: "#222", border: `1px solid ${borderGray}`, fontFamily: "'JetBrains Mono', 'Menlo', 'monospace" }}>{result}</pre>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.main>
    </div>
  );
}
