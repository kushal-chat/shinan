from agents import Agent, WebSearchTool
from pydantic import BaseModel
from context import ShinanContext
from ..prompts import Prompt

WRITER_INSTRUCTIONS = Prompt().get_writer_prompt()

class Report(BaseModel):
    """A financial research summary."""
    report: str
    """The report content."""

writer_agent = Agent[ShinanContext](
    name="WriterAgent",
    instructions=WRITER_INSTRUCTIONS,
    model="o4-mini", # Can change this to deep research?
    tools=[WebSearchTool()],
    output_type=Report,
)
