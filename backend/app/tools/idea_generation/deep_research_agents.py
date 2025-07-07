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

from agents import Agent, HostedMCPTool, WebSearchTool, FileSearchTool, ModelSettings, RunResult
from .guardrail_agent import sensitive_guardrail
from pydantic import BaseModel
from ..prompts import Prompt
from context import ShinanContext, context_tool
from typing import List

class Clarifications(BaseModel):
    questions: List[str]

prompts = Prompt()
INSTRUCTION_AGENT_PROMPT = prompts.instruction_prompt
CLARIFICATION_PROMPT = prompts.clarification_prompt
TRIAGE_PROMPT = prompts.triage_prompt
VERIFIER_PROMPT = prompts.verifier_prompt

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

class Verifier(BaseModel):
    """A verifier agent on whether things are relevant to the context."""
    is_relevant: bool
    improvement_suggestions: str

verifier_agent = Agent[ShinanContext](
    name="VerifierAgent",
    instructions=VERIFIER_PROMPT,
    model="o3-mini",
    output_type=Verifier,
)

async def _deep_research_context_relevance(run_result: RunResult) -> str:
    if not run_result.final_output.is_relevant:
        return (f"The message is not relevant to the context. Please include context in the message using the following suggestions: {run_result.final_output.improvement_suggestions}")
    else:
        return "The message is relevant to the context, return this."

verifier_tool = verifier_agent.as_tool(
    tool_name="verifier",
    tool_description="Use to verify the report is relevant to the context.",
    custom_output_extractor=_deep_research_context_relevance,
)

async def _context_relevance(run_result: RunResult) -> str:
    if not run_result.final_output.is_relevant:
        return (f"Not relevant to the context. Please improve the info using the following suggestions: {run_result.final_output.improvement_suggestions}")
    else:
        return "Is relevant to the context, return this."

research_tools = [
    WebSearchTool(),
    FileSearchTool(
        vector_store_ids=["vs_68642a4dab488191b7c7b089cf1abe3e"]
    ),
    verifier_agent.as_tool(
        tool_name="verifier",
        tool_description="Use to verify the report is relevant to the context.",
        custom_output_extractor=_context_relevance,
    )
]

research_agent = Agent[ShinanContext](
    name="Researcher",
    model="gpt-4o-mini",
    instructions="Perform deep empirical research based on the user's instructions.",
    tools=research_tools,
    model_settings=ModelSettings(tool_choice="required"),
)

instruction_agent = Agent[ShinanContext](
    name="Instructor",
    model="gpt-4o-mini",
    instructions=INSTRUCTION_AGENT_PROMPT,
    handoff_description="After receiving a clarified input, begins creation of prompt to instruct research agent.",
    handoffs=[research_agent],
)

clarifying_agent = Agent[ShinanContext](
    name="Clarifier",
    model="gpt-4o-mini",
    instructions=CLARIFICATION_PROMPT,
    output_type=Clarifications,
    handoffs=[instruction_agent],
    tools=[context_tool],
    model_settings=ModelSettings(tool_choice="required"),
)

triage_agent = Agent[ShinanContext](
    name="Triage",
    instructions=TRIAGE_PROMPT,
    handoffs=[clarifying_agent, instruction_agent],
    input_guardrails=[sensitive_guardrail],
)