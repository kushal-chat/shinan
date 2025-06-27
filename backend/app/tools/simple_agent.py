from agents import Agent
from pydantic import BaseModel

PROMPT = "Say hello to the user."

class Response(BaseModel):
    response: str

simple_agent = Agent(
    name="SimpleAgent",
    instructions=PROMPT,
    output_type=Response,
)