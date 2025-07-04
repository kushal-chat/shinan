from pydantic import BaseModel, Field
from typing import List

class ShinanContext(BaseModel):
    """A context for the Shinan client."""
    company: str = Field(..., description="Company name")
    role: str = Field(..., description="User's role")
    interests: List[str] = Field(..., description="List of user interests")

class ContextPayload(BaseModel):
    """Including user ID for Redis"""
    user_id: str
    context: ShinanContext