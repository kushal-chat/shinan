from agents import Agent, function_tool, WebSearchTool
from agents.model_settings import ModelSettings
from pydantic import BaseModel
from context import ShinanContext
from ..prompts import Prompt

class Materials(BaseModel):
    """A list of materials."""
    materials: list[str]

web_search_agent = Agent[ShinanContext](
    name="WebSearchAgent",
    instructions=Prompt().web_search_prompt,
    tools=[WebSearchTool()],
    model_settings=ModelSettings(tool_choice="required"),
    output_type=str,
)