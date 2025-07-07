from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.root import router as root_router
from pydantic import BaseModel

app = FastAPI(
    title="Shinan",
    description="Shinan is a platform for financial research and analysis",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(root_router)

# Hello, world!
@app.get("/")
async def read_root():
    return {"message": "Hello, World!"}
