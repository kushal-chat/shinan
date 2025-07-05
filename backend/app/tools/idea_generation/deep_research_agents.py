"""
This file defines agents for deep research workflows, inspired by the OpenAI Deep Research API agents example:
https://cookbook.openai.com/examples/deep_research_api/introduction_to_deep_research_api_agents

Specifically, this file implements a multi-stage agent workflow for deep research tasks, 
where each agent is responsible for a distinct phase: 
- triage (determining if clarifications are needed), 
- clarification (generating follow-up questions for the user), 
- instruction formulation (translating user needs into actionable research instructions), and 
- execution (performing research using web search and file search tools). 

Agents are connected via explicit handoffs to ensure a structured and modular research process.
"""

from faulthandler import is_enabled
from agents import Agent, HostedMCPTool, input_guardrail, Runner, GuardrailFunctionOutput, WebSearchTool, FileSearchTool, handoff, ModelSettings
from pydantic_core.core_schema import model_ser_schema
from .guardrail_agent import sensitive_guardrail
from agents.run_context import RunContextWrapper
from pydantic import BaseModel
from ..prompts import Prompt
from context import ShinanContext, context_tool
from typing import List

class Clarifications(BaseModel):
    questions: List[str]

prompts = Prompt()
INSTRUCTION_AGENT_PROMPT = prompts.get_deep_research_instruction_prompt()
CLARIFICATION_PROMPT = prompts.get_clarification_prompt()
intro_phrases = [
    "I have a few questions to clarify",
    "I wanted to make sure we're on the same page",
    "Let me ask a few questions to better understand",
    "I'd like to clarify a few things",
    "To give you the best help, I need to understand a bit more",
    "Let me gather some details to assist you better",
    "I want to make sure I understand your needs correctly",
    "A few quick questions to point me in the right direction"
]

# FileSearchTool(vector_store_ids=["vs_68642a4dab488191b7c7b089cf1abe3e"])

assistant_agent = Agent[ShinanContext](
    name="Assistant Agent",
    model="gpt-4o-mini",
    instructions=(
        "You answer short, followup questions relating to the previous discussion and report.\n"
        "Use MCP resources and others to respond to questions. Keep the discussion close to the context.\n"""
        "Decide whether a new full-length research task has been given explicitly.\n"
        "• If yes → call transfer_to_triage_agent.\n"
    ),
    handoff_description=("A helpful assistant that answers short, followup questions relating to the previous discussion and report."),
    tools=[
        WebSearchTool(),
        FileSearchTool(vector_store_ids=["vs_68642a4dab488191b7c7b089cf1abe3e"])

        # TODO: Implement MCP as a tool
        # NOTE: May not work with Cursor application
        # HostedMCPTool(
        #         tool_config={
        #             "type": "mcp",
        #             "server_label": "file_search",
        #             "server_url": "http://0.0.0.0:8000/sse",
        #             "require_approval": "never",}
    ],
)

research_agent = Agent[ShinanContext](
    name="Research Agent",
    model="gpt-4o-mini", 
    # TODO: Replace with web_search_preview so as to allow Deep Research to run
    instructions="Perform deep empirical research based on the user's instructions.",
    tools=[WebSearchTool(), FileSearchTool(vector_store_ids=["vs_68642a4dab488191b7c7b089cf1abe3e"])],
    model_settings=ModelSettings(tool_choice="required"),
    handoffs=[assistant_agent]
)

instruction_agent = Agent[ShinanContext](
    name="Research Instruction Agent",
    model="gpt-4o-mini",
    instructions=INSTRUCTION_AGENT_PROMPT,
    handoffs=[research_agent],
)

clarifying_agent = Agent[ShinanContext](
    name="Clarifying Questions Agent",
    model="gpt-4o-mini",
    instructions=CLARIFICATION_PROMPT,
    output_type=Clarifications,
    handoffs=[instruction_agent],
    tools=[context_tool],
    model_settings=ModelSettings(tool_choice="required"),
)

triage_agent = Agent[ShinanContext](
    name="Triage Agent",
    instructions=(
        "Almost always ask clarifying questions to provide the best possible help.\n"
        "• Unless the request is 100% clear and specific → call transfer_to_clarifying_questions_agent\n"
        "• Only if absolutely no clarification could improve the response → call transfer_to_research_instruction_agent\n"
        "Return exactly ONE function-call."
    ),
    handoffs=[handoff(clarifying_agent), instruction_agent], 
    input_guardrails=[sensitive_guardrail],
)