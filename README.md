# Shinan - LLM Chat & Research Platform

A modern, full-stack AI research and chat platform with real-time agent feedback, file (PDF/PNG) upload, and context-aware conversations.  
Built with **FastAPI** (Python) and **Next.js** (React/TypeScript).

---

## ✨ Features

- **Conversational AI**: Chat with an LLM-powered agent, with real-time progress feedback.
- **Context Prompt**: On first use, users provide company, role, and interests to personalize the experience.
- **File Upload**: Upload PDF or PNG files for analysis and research (with OCR for PNGs).
- **Agent Progress Streaming**: See live updates as the backend processes your query (e.g., "Generating ideas...", "Researching web...", "Writing report...").
- **Modern UI**: Clean, green-themed interface with smooth animations (Framer Motion).
- **Internationalization**: Friendly Japanese/English feedback messages.
- **Dockerized**: Easy to run locally or deploy in production.

---

## 🏗️ Architecture

- **Backend**: FastAPI (Python) - RESTful API, async, streaming support
- **Frontend**: Next.js (React/TypeScript) - Modern SPA, Framer Motion
- **Containerization**: Docker & Docker Compose

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop (recommended)
- Python 3.10+
- Node.js 18+

### 1. Clone the repository

```bash
git clone <repository-url>
cd shinan
```

### 2. Start with Docker Compose

```bash
docker-compose up --build
```

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### 3. Local Development

#### Backend

```bash
cd backend/app
uv sync
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

---

## 🖥️ User Experience

- On first visit, users are prompted for **context** (company, role, interests).
- **Chat**: Type a question and see real-time agent progress (steps) and the final answer.
- **Upload**: Upload a PDF or PNG for analysis. Results appear in a chat bubble.
- **Feedback**: After sending a message, a friendly "Thank you for using me, hang on a bit! ご利用、ありがとうございます！少々お待ちください。" message appears before agent steps.

---

## 🛠️ API Endpoints

### `/client/context` (POST)
Set the user context (company, role, interests).

### `/client/query` (POST)
Submit a chat query. Returns the final answer (non-streaming).

### `/client/query/stream` (POST)
Submit a chat query and receive real-time progress updates and the final answer as a stream.

### `/client/upload` (POST)
Upload a PDF or PNG for analysis. Returns the analysis result.

---

## 🧩 Frontend Components

- **ContextPrompt**: Modal for entering user context.
- **FileUpload**: Button for uploading PDF/PNG, shows results in chat style.
- **Chat UI**: Modern, animated chat with agent progress and bot/user bubbles.

---

## 🧪 Testing

### Backend

```bash
cd backend/app
uv run pytest
```

### Frontend

```bash
cd frontend
npm test
```

---

## 🐳 Docker

```bash
docker-compose up --build
```

---

## 📄 License

MIT License

---

**Enjoy using Shinan!**  
For questions or contributions, open an issue or pull request. 