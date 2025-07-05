from agents import (
    Agent, 
    function_tool,
    RunContextWrapper,
    ModelSettings,
)
from .guardrail_agent import sensitive_guardrail
from pydantic import BaseModel
from typing import Sequence
from context import ShinanContext, context_tool
from ..prompts import Prompt

class SearchIdea(BaseModel):
    """
    A search idea. 
    Defines:
    - query: The search idea.
    - reasoning: Why this is a good search idea in context of the text.
    """
    query: str
    reasoning: str

class SearchIdeas(BaseModel):
    """A list of search ideas."""
    ideas: Sequence[SearchIdea]

class MaterialInsightPoint(BaseModel):
    """
    Input to the report generation agent.
    Defines:
    - material_analysis: A point of interest analysis of the material.
    - point_of_interest: Where in the material this was found.
    - reasoning: Why this analysis is relevant in context of the material.
    """
    material_analysis: str
    point_of_interest: str
    reasoning: str

class MaterialInsights(BaseModel):
    """
    A list of material analysis points.
    """
    insights: Sequence[MaterialInsightPoint]

class Analysis(BaseModel):
    """A list of search ideas and material analysis points."""
    ideas: SearchIdeas
    insights: MaterialInsights

SEARCH_PROMPT = Prompt().get_material_prompt()

material_agent = Agent[ShinanContext](
    name="MaterialAgent",
    instructions=SEARCH_PROMPT,
    model="o4-mini", # Note that o3-mini does not accept images.
    output_type=Analysis,
    tools=[context_tool],
    model_settings=ModelSettings(tool_choice="required"),
    input_guardrails=[sensitive_guardrail],
)