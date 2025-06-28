from agents import Agent
from pydantic import BaseModel
from context import ShinanContext
from ..prompts import Prompt

PROMPT = (
    "You are a financial research summary writer. Given a query and a list of search results, "
    "Give a single sentence summary report."
)

class Report(BaseModel):
    """A financial research summary."""
    report: str
    """The report content."""

writer_agent = Agent[ShinanContext](
    name="WriterAgent",
    instructions=Prompt().writer_prompt,
    model="o3-mini",
    output_type=Report,
    tool_use_behavior='run_llm_again'
)