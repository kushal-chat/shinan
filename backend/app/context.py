from pydantic import BaseModel, Field
from typing import List
from agents import RunContextWrapper, function_tool

class ShinanContext(BaseModel):
    """A context for the Shinan client."""
    company: str = Field(..., description="Company name")
    role: str = Field(..., description="User's role")
    interests: List[str] = Field(..., description="List of user interests")

@function_tool
def context_tool(ctx: RunContextWrapper[ShinanContext]) -> str:
    """
    Test to retrieve the current agent context to enable informed decision-making and maintain operational awareness. 
    Returns: context.
    """
    return ctx.context.company, ctx.context.role, ctx.context.interests