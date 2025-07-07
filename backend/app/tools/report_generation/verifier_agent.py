from agents import Agent
from pydantic import BaseModel
from context import ShinanContext
from ..prompts import Prompt

prompts = Prompt()
VERIFIER_INSTRUCTIONS = prompts.get_verifier_prompt()

class Verification(BaseModel):
    """A verifier agent."""
    is_relevant: bool
    improvement_suggestions: str
    """How to improve the report."""

verifier_agent = Agent[ShinanContext](
    name="VerifierAgent",
    instructions=VERIFIER_INSTRUCTIONS,
    model="o3-mini",
    output_type=Verification,
)