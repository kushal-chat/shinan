from agents import Agent, HostedMCPTool, function_tool, WebSearchTool, FileSearchTool
from agents.model_settings import ModelSettings
from pydantic import BaseModel
from context import ShinanContext
from ..prompts import Prompt
import requests
from bs4 import BeautifulSoup

prompts = Prompt()
SEARCH_PROMPT = prompts.get_web_search_prompt()

class Materials(BaseModel):
    """A list of materials."""
    materials: list[str]

@function_tool
def softbank_blogs() -> str:
    """Scrape information from newest Softbank blogs"""
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

search_agent = Agent[ShinanContext](
    name="Searcher",
    instructions=Prompt().web_search_prompt,
    tools=[
        WebSearchTool(),
        # FileSearchTool(vector_store_ids=["vs_68642a4dab488191b7c7b089cf1abe3e"]),
        softbank_blogs
    ],
    model_settings=ModelSettings(tool_choice="required"),
    output_type=str,
)