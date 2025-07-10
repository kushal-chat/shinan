from agents import Agent, HostedMCPTool, function_tool, WebSearchTool, FileSearchTool
from agents.model_settings import ModelSettings
from pydantic import BaseModel
from context import ShinanContext
from ..prompts import Prompt
import requests
from bs4 import BeautifulSoup

prompts = Prompt()
SEARCH_PROMPT = prompts.get_web_search_prompt()

search_agent = Agent[ShinanContext](
    name="Searcher",
    instructions=Prompt().web_search_prompt,
    tools=[
        WebSearchTool(),
    ],
    model="gpt-4o-mini",
    model_settings=ModelSettings(tool_choice="required"),
    output_type=str,
)