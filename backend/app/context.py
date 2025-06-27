from pydantic import BaseModel
from typing import List

class ShinanContext(BaseModel):
    """A context for the Shinan client."""
    company: str
    role: str
    interests: List[str]