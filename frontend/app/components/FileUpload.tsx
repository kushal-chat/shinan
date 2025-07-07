import React, { useRef, useState, useEffect } from "react";

import { motion, AnimatePresence } from "framer-motion";
import { Toaster, toast } from "sonner";

type ButtonState = "idle" | "loading" | "success" | "error";

const buttonVariants = {
  idle: {
    backgroundColor: "#FF0000",
    scale: 1,
    boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
    transition: { duration: 0.3 },
  },
  loading: {
    backgroundColor: "#3bb273",
    scale: 1.1,
    boxShadow: "0 6px 16px rgba(59,178,115,0.6)",
    transition: {
      repeat: Infinity,
      repeatType: "mirror" as const,
      duration: 1.1,
      backgroundColor: { duration: 0.25 },
      boxShadow: { duration: 0.25 },
      scale: { duration: 0.4 },
    },
  },
  success: {
    backgroundColor: "#3bb273",
    scale: 1.1,
    boxShadow: "0 6px 16px rgba(59,178,115,0.6)",
    transition: { duration: 0.5 },
  },
  error: {
    backgroundColor: "#d9534f",
    scale: 1.1,
    boxShadow: "0 6px 16px rgba(217,83,79,0.6)",
    transition: { duration: 0.4 },
  },
};

const RotatingCircle: React.FC = () => (
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
);

const buttonTextMap: Record<ButtonState, React.ReactNode> = {
  idle: "Upload PDF or PNG",
  loading: (
    <span style={{ display: "inline-flex", alignItems: "center" }}>
      <RotatingCircle />
      Uploading...
    </span>
  ),
  success: "Uploaded!",
  error: "Upload Failed - Retry",
};

const FileUpload: React.FC<{ onResult: (result: string) => void }> = ({ onResult }) => {
  const [loading, setLoading] = useState(false);
  const [buttonState, setButtonState] = useState<ButtonState>("idle");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [note, setNote] = useState("");

  // Reset button state after success/error delay
  useEffect(() => {
    if (buttonState === "success" || buttonState === "error") {
      const timer = setTimeout(() => {
        setButtonState("idle");
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [buttonState]);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;

    setLoading(true);
    setButtonState("loading");

    const formData = new FormData();
    formData.append("file", file);
    if (note.trim()) formData.append("note", note);

    setTimeout(() => {
      toast("Thank you for using me, hang on a bit! ご利用、ありがとうございます！少々お待ちください。");
    }, 1000);

    try {
      const res = await fetch("http://localhost:8000/client/upload", {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      onResult(typeof data === "string" ? data : data.result || JSON.stringify(data));
      setButtonState("success");
    } catch (error: any) {
      onResult(error.message);
      setButtonState("error");
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
      setNote("");
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center" }}>
      <motion.button
        type="button"
        onClick={() => fileInputRef.current?.click()}
        disabled={loading}
        variants={buttonVariants}
        animate={buttonState}
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
        {buttonTextMap[buttonState]}
      </motion.button>
      <input
        ref={fileInputRef}
        type="file"
        accept="application/pdf,image/png"
        style={{ display: "none" }}
        onChange={handleFileChange}
      />
    </div>
  );
}

export default FileUpload;
