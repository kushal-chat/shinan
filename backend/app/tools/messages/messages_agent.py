from agents import Agent, RunContextWrapper
from context import ShinanContext

def context_instructions(
    context: RunContextWrapper[ShinanContext], agent: Agent[ShinanContext]
) -> str:
    PROMPT = f"""
        You are a helpful assistant who greets the user and engages them in friendly conversation. 
        You understand the user's context that they are a {context.context.role} at {context.context.company} and have interests in {context.context.interests}
        Reference the context often, and things mentioned earlier in the conversation, like searches and websites.
        Ask thoughtful questions or make comments related to their interests, role, or company to encourage further conversation.
    """

    return PROMPT

messages_agent = Agent[ShinanContext](
    name="Messager",
    instructions=context_instructions,
    model="gpt-4.1-nano",
    output_type=str
)