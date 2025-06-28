from agents import Agent
from pydantic import BaseModel
from context import ShinanContext
from ..prompts import Prompt

class Verifier(BaseModel):
    """A verifier agent."""
    is_relevant: bool
    improvement_suggestions: str
    """How to improve the report."""

verifier_agent = Agent[ShinanContext](
    name="VerifierAgent",
    instructions=Prompt().verifier_prompt,
    model="o3-mini",
    output_type=Verifier,
)