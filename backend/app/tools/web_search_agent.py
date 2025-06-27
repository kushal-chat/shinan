from agents import Agent, function_tool, WebSearchTool
from agents.model_settings import ModelSettings
from pydantic import BaseModel

PROMPT = (
    "You are a web search agent. Given a search term, "
    "obtain a multimodal blog post or relevant article."
)

class Materials(BaseModel):
    """A list of materials."""
    materials: list[str]


web_search_agent = Agent(
    name="WebSearchAgent",
    instructions=PROMPT,
    # mcp_servers=["brave", "fetch"],
    tools=[WebSearchTool()],
    model_settings=ModelSettings(tool_choice="required"),
    output_type=str,
)