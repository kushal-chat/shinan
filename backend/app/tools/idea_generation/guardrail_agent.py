from agents import Agent, input_guardrail, Runner, GuardrailFunctionOutput
from agents.run_context import RunContextWrapper
from pydantic import BaseModel
from ..prompts import Prompt

GUARDRAIL_PROMPT = Prompt().get_guardrail_prompt()

class IsSensitive(BaseModel):
    is_sensitive: bool
    reason: str

guardrail_agent = Agent(
    name="GuardrailAgent",
    instructions= GUARDRAIL_PROMPT,
    output_type=IsSensitive,
)

@input_guardrail
async def sensitive_guardrail(ctx: RunContextWrapper, agent: Agent, input: str) -> GuardrailFunctionOutput:
    """Guardrail for the idea agent."""
    result = await Runner.run(guardrail_agent, input, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_sensitive,  
    )