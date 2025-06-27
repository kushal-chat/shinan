from agents import Agent, input_guardrail, Runner, GuardrailFunctionOutput
from agents.run_context import RunContextWrapper
from pydantic import BaseModel

class IsABanana(BaseModel):
    is_a_banana: bool
    reason: str

guardrail_agent = Agent(
    name="GuardrailAgent",
    instructions="You are a guardrail agent. You are given a query and you need to determine if it has a banana in it.",
    output_type=IsABanana,
)

@input_guardrail
async def banana_guardrail(ctx: RunContextWrapper, agent: Agent, input: str) -> GuardrailFunctionOutput:
    """Guardrail for the idea agent."""
    result = await Runner.run(guardrail_agent, input, context=ctx.context)

    return GuardrailFunctionOutput(
        output_info=result.final_output,
        tripwire_triggered=result.final_output.is_a_banana,  
    )