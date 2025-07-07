from ast import Mod
from agents import (
    Agent, 
    RunContextWrapper, 
    WebSearchTool, 
    HostedMCPTool,
    function_tool,
    ModelSettings
)
from pydantic import BaseModel
from context import ShinanContext
from ..prompts import Prompt
import requests
from bs4 import BeautifulSoup

WRITER_INSTRUCTIONS = Prompt().get_writer_prompt()

class Report(BaseModel):
    """A financial research summary."""
    report: str
    """The report content."""

instructions_with_blogs = WRITER_INSTRUCTIONS

writer_agent = Agent[ShinanContext](
    name="WriterAgent",
    instructions=WRITER_INSTRUCTIONS,
    model="o4-mini", 
    tools=[
        WebSearchTool(),
    ],
    output_type=str,
)

deep_research_agent = Agent[ShinanContext](
    name="DeepResearchAgent",
    instructions=WRITER_INSTRUCTIONS,
    model="o4-mini-deep-research-2025-06-26",
    tools=[
        WebSearchTool(),
        HostedMCPTool(
            tool_config={
                "type": "mcp",
                "server_label": "file_search",
                "server_url": "http://localhost:8080/sse",
                "require_approval": "never",
            }
        )
    ],
    output_type=str,
)