# Shinan 指南

A full-stack platform built using new OpenAI Agents SDK and MCP technology with real-time agent feedback, orchestration, file (PDF/PNG) upload, and context-aware conversations.  
Built with **FastAPI** (Python) and **Next.js** (React/TypeScript), and containerized on Docker. Deployed on Vercel and Railway (in progress).

Please see [kushalc.framer.ai](https://kushalc.framer.ai) for blog posts detailing progress and architecture.

---

## Architecture

### Frameworks
- **Backend**: FastAPI (Python) - RESTful API, async, streaming support, OpenAI Agents SDK + MCP
- **Frontend**: Next.js (React/TypeScript), Tailwind CSS 
- **Containerization**: Docker & Docker Compose, as well as Supervisor for backend

### Technologies
- *Orchestration of Multiagent AI Systems*, the core principle of 指南 for analysis, research, compiling, MCPs, etc. More to come.
- *AI Agent Tools*
    - *Context Management* for aligning responses with user’s context (i.e. CFO at AI lab, student)
    - *Guardrail Agents* for sensitive material input prevention.
    - *Prompt Engineering* for accurate tool usage and handoffs.
        - *Chain-of-Thought Prompting* to elicit reasoning per the [GPT 4.1 Prompting Guide](https://cookbook.openai.com/examples/gpt4-1_prompting_guide)
        - *Dynamic Instruction* capabilities for more targeted searches.
    - *Tools*
        - *OpenAI Hosted Tools* like `WebSearch()`, `FileSearchTool()`, `HostedMCP`
        - *Function Tools* for verification, context retrieval, etc.
        - *Agents as Tools* for verifier agent.
    - *Structured Outputs* with Pydantic throughout.
    - *asyncio (Asynchronous Development)* for complex engineering tasks like streaming multiple concurrent searches and streaming entire research in real-time.
    - *Handoffs*
    - *FastAPI* extensively for routing, sending streaming updates to frontend, and CORS middleware
    - *FastMCP* and generally *MCP* for connecting to vector store
    - *OpenAI Vector Stores* for files
        - *Llama-Index* to a small extent to review other vector store options.
    - *Visualization* for visualizing backend workflow
    - *OpenAI Models* in choosing optimal models, using VLM when needed
    - *Deep Research API*
        - *Citation*
    - *etc.*
- *OpenAI Responses API* as a foundation, particularly for TResponseInputItem and Deep Research API
- *OCR* as `pytesseract` for OCR on PDFs / images for text
- *Redis* which I intend to integrate for persistency
- *MCP Integrations with Applications* like Cursor and Claude Desktop
- *Docker*, *Docker-Compose* and *Supervisor* applied to monorepos of Next.js + Python
    - *Railway* and *Vercel* for deployment, and gained some knowhow surrounding middleware bug fixing
- *etc.*

---

## Quick Start

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

---

## User Experience

- On first visit, users are prompted for **context** (company, role, interests).
- **Chat**: Type a question and see real-time agent progress (steps) and the final answer. (Research, Messages, and Deep Research modes available)
- **Upload**: Upload a PDF or PNG for analysis. Results appear in a chat bubble.

---

## API Endpoints

### `/client/context` (POST)
Set the user context (company, role, interests).

### `/client/query` (POST)
Submit a chat query. Returns the research result.

### `/client/messages` (POST)
Messages for simple chat queries (i.e. follow-ups). Returns the final answer, taking into account most recent report.

### `/client/deep-research` (POST)
Calls OpenAI Deep Research via Responses API. Returns the final answer.

### `/client/upload` (POST)
Upload a PDF or PNG for analysis. Returns the analysis result.

---

## Frontend Components

- **ContextPrompt**: Modal for entering user context.
- **FileUpload**: Button for uploading PDF/PNG, shows results in chat style.
- **Chat**: Modern, animated chat with agent progress and bot/user bubbles.

## License

MIT
