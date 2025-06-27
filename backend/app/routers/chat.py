from fastapi import APIRouter, Body
from pydantic import BaseModel
from .client import manager

router = APIRouter()

class ChatRequest(BaseModel):
    query: str
    filename: str = None  # Optional

@router.post("/chat")
async def chat(req: ChatRequest):
    # If you want to use the file, you can pass req.filename to manager.run
    result = await manager.run(req.query)
    return {"result": result} 