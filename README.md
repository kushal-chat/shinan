# Shinan - LLM Chat Application

A modern, full-stack LLM chat application built with FastAPI backend and Next.js frontend.

## 🏗️ Architecture

- **Backend**: FastAPI (Python) - RESTful API with async support
- **Frontend**: Next.js (React/TypeScript) - Modern web interface
- **Containerization**: Docker & Docker Compose
- **Package Management**: UV (Python), npm (Node.js)

## 🚀 Quick Start

### Prerequisites
- Docker Desktop
- Python 3.13+
- Node.js 20+

### Development Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd shinan
   ```

2. **Start with Docker Compose**
   ```bash
   docker-compose up --build
   ```

3. **Access the application**
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Local Development

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

## 📁 Project Structure

```
shinan/
├── docker-compose.yml          # Multi-service orchestration
├── backend/
│   └── app/
│       ├── main.py            # FastAPI application entry point
│       ├── routers/           # API route modules
│       ├── pyproject.toml     # Python dependencies
│       └── Dockerfile         # Backend container
├── frontend/
│   ├── app/                   # Next.js app directory
│   ├── components/            # React components
│   ├── package.json           # Node.js dependencies
│   └── Dockerfile             # Frontend container
└── README.md                  # This file
```

## 🛠️ Development

### Adding New API Endpoints
1. Create new router in `backend/app/routers/`
2. Import and include in `main.py`
3. Update API documentation

### Adding New Frontend Features
1. Create components in `frontend/components/`
2. Add pages in `frontend/app/`
3. Update TypeScript types as needed

## 🐳 Docker

### Build Images
```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build backend
docker-compose build frontend
```

### Run Services
```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# View logs
docker-compose logs -f
```

## 🔧 Configuration

### Environment Variables
Create `.env` files for local development:

```bash
# backend/app/.env
OPENAI_API_KEY=your_api_key_here
DATABASE_URL=postgresql://user:pass@localhost/db

# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🧪 Testing

### Backend Tests
```bash
cd backend/app
uv run pytest
```

### Frontend Tests
```bash
cd frontend
npm test
```

## 📦 Deployment

### Production Build
```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details 