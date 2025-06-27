from agents import (
    Agent, 
)
from .guardrail_agent import banana_guardrail
from pydantic import BaseModel
from typing import Sequence

PROMPT = (
    "You are a financial research planner. Given a request for financial analysis, "
    "produce a set of web searches to gather the context needed. Aim for recent "
    "headlines, earnings calls or 10‑K snippets, analyst commentary, and industry background. "
    "Output less than 3 search terms to query for."
)

class Idea(BaseModel):
    """A search idea and reason."""
    query: str
    reason: str

class Ideas(BaseModel):
    """A list of search ideas."""
    ideas: Sequence[Idea]

idea_agent = Agent(
    name="IdeaAgent",
    instructions=PROMPT,
    model="o3-mini",
    output_type=Ideas,
    input_guardrails=[banana_guardrail],
)