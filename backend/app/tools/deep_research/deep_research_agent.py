from agents import Agent, input_guardrail, Runner, GuardrailFunctionOutput
from agents.run_context import RunContextWrapper
from pydantic import BaseModel
from ..prompts import Prompt
from agents.tools.hosted_mcp import HostedMCPTool
from agents.tools.web_search import WebSearchTool

research_agent = Agent(
    name="Research Agent",
    model="o3-deep-research-2025-06-26",
    instructions=Prompt().deep_research_prompt,
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