from agents import (
    Agent,
    ModelSettings,
)
from typing import Sequence
from pydantic import BaseModel
from agents.extensions.handoff_prompt import prompt_with_handoff_instructions

from .guardrail_agent import sensitive_guardrail
from .material_idea_agent import material_agent
from .text_idea_agent import text_agent

from ..prompts import Prompt
from context import ShinanContext, context_tool

prompts = Prompt()
CLARIFICATION_PROMPT = prompts.get_clarification_prompt()

clarification_agent = Agent[ShinanContext](
    name = "Clarifier",
    instructions=prompt_with_handoff_instructions(CLARIFICATION_PROMPT),
    handoff_description="Clarifies vague queries to lead to better search ideas.",
    model="gpt-4.1-nano-2025-04-14", 
    output_type=str,
    tools=[context_tool],
    model_settings=ModelSettings(tool_choice="required"),
)