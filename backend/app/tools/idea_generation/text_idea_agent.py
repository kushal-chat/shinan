from agents import (
    Agent, 
    function_tool,
    RunContextWrapper,
)
from .guardrail_agent import sensitive_guardrail
from pydantic import BaseModel
from typing import Sequence
from context import ShinanContext
from ..prompts import Prompt
from agents.model_settings import ModelSettings

class SearchIdea(BaseModel):
    """
    A search idea. 
    Defines:
    - query: The search idea.
    - reasoning: Why this is a good search idea in context of the text.
    """
    query: str
    reasoning: str

class SearchIdeas(BaseModel):
    """A list of search ideas."""
    ideas: Sequence[SearchIdea]

@function_tool
def context_tool(ctx: RunContextWrapper[ShinanContext]) -> str:
    """
    Test to retrieve the current agent context to enable informed decision-making and maintain operational awareness. 
    Returns: context.
    """
    return ctx.context.company, ctx.context.role, ctx.context.interests

prompt = Prompt().text_prompt

text_agent = Agent[ShinanContext](
    name="TextAgent",
    instructions=prompt,
    model="o3-mini", # Note that o3-mini does not accept images.
    output_type=SearchIdeas,
    tools=[context_tool],
    model_settings=ModelSettings(tool_choice="required"),
)