from agents import Agent
from pydantic import BaseModel

PROMPT = (
    "You are a financial research summary writer. Given a query and a list of search results, "
    "Give a single sentence summary report."
)

class Report(BaseModel):
    """A financial research summary."""
    report: str
    """The report content."""

writer_agent = Agent(
    name="WriterAgent",
    instructions=PROMPT,
    model="o3-mini",
    output_type=Report,
)