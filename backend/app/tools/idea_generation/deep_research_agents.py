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

from agents import Agent, input_guardrail, Runner, GuardrailFunctionOutput, WebSearchTool, HostedMCPTool
from .guardrail_agent import sensitive_guardrail
from agents.run_context import RunContextWrapper
from pydantic import BaseModel
from ..prompts import Prompt
from context import ShinanContext
from typing import List

class Clarifications(BaseModel):
    questions: List[str]

prompts = Prompt()
INSTRUCTION_AGENT_PROMPT = prompts.get_deep_research_instruction_prompt()
CLARIFICATION_PROMPT = prompts.get_clarification_prompt()

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
    tools=[WebSearchTool(),
           HostedMCPTool(
            tool_config={
                "type": "mcp",
                "server_label": "file_search",
                "server_url": "https://<url>/sse",
                "require_approval": "never",
            }
            )
        ]
)

research_agent = Agent[ShinanContext](
    name="Research Agent",
    model="o3-deep-research-2025-06-26",
    instructions="Perform deep empirical research based on the user's instructions.",
    tools=[WebSearchTool(),
           HostedMCPTool(
            tool_config={
                "type": "mcp",
                "server_label": "file_search",
                "server_url": "http://0.0.0.0:8000/sse/",
                "require_approval": "never",
            }
            )
        ],
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
)

triage_agent = Agent[ShinanContext](
    name="Triage Agent",
    instructions=(
        "Call transfer_to_research_instruction_agent"
        # "Decide whether clarifications are required.\n"
        # "• If yes → call transfer_to_clarifying_questions_agent\n"
        # "• If no  → call transfer_to_research_instruction_agent\n"
        # "Return exactly ONE function-call."
    ),
    handoffs=[instruction_agent], # clarifying_agent, 
    input_guardrails=[sensitive_guardrail],
)