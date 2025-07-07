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

@function_tool
def softbank_blogs() -> str:
    search_endpoint = "https://www.softbank.jp/sbnews"

    response = requests.get(search_endpoint)
    soup = BeautifulSoup(response.text, 'html.parser')
    items = soup.select('li.urllist-item.recent-entries-item')
    blogs = ""

    for item in items:
        title_tag = item.select_one('a.urllist-title-link')
        title = title_tag.text.strip() if title_tag else 'No title'
        article_url = title_tag['href'] if title_tag else 'No URL'
        blogs+=(f"Title: {title}, URL: {article_url}\n")

    return blogs

writer_agent = Agent[ShinanContext](
    name="WriterAgent",
    instructions=WRITER_INSTRUCTIONS,
    model="o4-mini", 
    tools=[
        WebSearchTool(),
        softbank_blogs
    ],
    output_type=Report,
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
    output_type=Report,
)