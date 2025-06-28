import React, { useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";

const FileUpload: React.FC = () => {
  const [result, setResult] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    setLoading(true);
    setResult(null);
    const formData = new FormData();
    formData.append("file", file);
    try {
      const response = await fetch("http://localhost:8000/client/upload", {
        method: "POST",
        body: formData,
      });
      if (!response.ok) {
        throw new Error("Upload failed");
      }
      const data = await response.json();
      setResult(typeof data === "string" ? data : data.result || JSON.stringify(data));
    } catch (error: any) {
      setResult(error.message);
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <div style={{ width: "100%", display: "flex", flexDirection: "column", alignItems: "center" }}>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf,image/png"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />
      <button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={loading}
        style={{
          background: loading ? "#b6e2c6" : "#3bb273",
          color: "#fff",
          border: "none",
          borderRadius: 10,
          padding: "14px 32px",
          fontWeight: 700,
          fontSize: 18,
          cursor: loading ? "not-allowed" : "pointer",
          marginBottom: 32,
          boxShadow: "0 2px 8px rgba(59,178,115,0.08)",
          transition: "background 0.2s"
        }}
      >
        {loading ? "Uploading..." : "Upload PDF or PNG"}
      </button>
      <AnimatePresence>
        {result && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.4 }}
            style={{
              alignSelf: "flex-start",
              maxWidth: "80%",
              background: "#e6f9ed",
              color: "#1a3d2f",
              borderRadius: 14,
              padding: "14px 20px",
              fontSize: 17,
              boxShadow: "0 2px 8px rgba(59,178,115,0.08)",
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              marginTop: 8
            }}
          >
            {result}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};

export default FileUpload; 