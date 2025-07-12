from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.root import router as root_router
from pydantic import BaseModel

app = FastAPI(
    title="Shinan",
    description="Shinan is a platform for AI agents to conduct relevant research.",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(root_router)
