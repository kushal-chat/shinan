from agents import (
    Agent, 
    function_tool,
    RunContextWrapper,
)
from .guardrail_agent import sensitive_guardrail
from pydantic import BaseModel
from typing import Sequence
from context import ShinanContext
from .prompts import Prompt

class Idea(BaseModel):
    """
    A search idea. 
    Defines:
    - query: The search idea.
    - point_of_interest: Where in the slide this was found.
    - reasoning: Why this is a good search idea in context of the material.
    """
    query: str
    point_of_interest: str
    reasoning: str

class Ideas(BaseModel):
    """A list of search ideas."""
    ideas: Sequence[Idea]

@function_tool
def context_tool(ctx: RunContextWrapper[ShinanContext]) -> str:
    """
    Test to retrieve the current agent context to enable informed decision-making and maintain operational awareness. 
    Returns: context.
    """
    return ctx.context.company, ctx.context.role, ctx.context.interests

prompt = Prompt().material_prompt

material_agent = Agent[ShinanContext](
    name="MaterialAgent",
    instructions=prompt,
    model="o4-mini", # Note that o3-mini does not accept images.
    output_type=Ideas,
    tools=[context_tool],
    input_guardrails=[sensitive_guardrail],
)