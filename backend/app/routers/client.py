import asyncio
from typing import Sequence, Optional
import io
import fitz
import pytesseract
from PIL import Image

from fastapi import APIRouter, Form, File, UploadFile, HTTPException
from pydantic import BaseModel
from agents import InputGuardrailTripwireTriggered, Runner, RunResult, custom_span, gen_trace_id, trace
from agents.mcp import MCPServer, MCPServerStreamableHttp

from tools.simple_agent import simple_agent, Response
from tools.idea_agent import idea_agent, Idea, Ideas
from tools.web_search_agent import web_search_agent
from tools.writer_agent import writer_agent, Report

router = APIRouter(prefix="/client", tags=["client"])

class ShinanQuery(BaseModel):
    """A query to the Shinan client."""
    query: str

class SimpleManager:
    """A simple manager that runs a simple agent."""
    
    def __init__(self) -> None:
        pass

    async def run(self, query: str) -> Response:
        result = await Runner.run(simple_agent, query)
        return result.final_output_as(Response)

class ShinanIntelligence:
    """A class that orchestrates the full flow of Shinan Intelligence."""
    
    def __init__(self) -> None:
        pass

    async def run(self, query: str, context: Optional[dict] = None) -> str:
        trace_id = gen_trace_id()

        with trace("Shinan Intelligence Workflow", trace_id=trace_id):
            
            # NOTE: This can be classes and like iterating over them
            ideas : list[str] = await self._generate_search_ideas(query, context=context)
            articles : list[str] = await self._research_web(ideas)
            # material_analysis : list[str] = await self._analyze_material(articles)

            report : str = await self._generate_report(query, articles)

            return str(report.report)


    async def _generate_search_ideas(self, query: str, context: Optional[dict] = None) -> Ideas:
        """Generate a list of search ideas for a given query."""

        try:
            result = await Runner.run(idea_agent, query)
            return result.final_output_as(Ideas)
        
        except InputGuardrailTripwireTriggered as e:
            print(f"This input is not allowed because it has a banana! {e}")
            return Ideas(ideas=[])


    async def _research_web(self, search_ideas: Ideas) -> Sequence[str]:
        """Search the web for a given idea."""

        with custom_span("Search the web"):
            tasks = [asyncio.create_task(self._search(idea)) for idea in search_ideas.ideas]
            results: list[str] = []
            num_completed = 0
            for task in asyncio.as_completed(tasks):
                result = await task
                if result is not None:
                    results.append(result)
                num_completed += 1
            return results

    async def _generate_report(self, query: str, search_results: Sequence[str]) -> str:
        """Generate a report from a query and search results."""

        result = await Runner.run(writer_agent, f"Query: {query}\nSearch results: {search_results}")
        
        return result.final_output_as(Report)

    async def _search(self, idea: Idea) -> str | None:
        """Search the web for a given idea."""

        print(f"Searching: {idea.query} - {idea.reason}")
        input_data = f"Search term: {idea.query}\nReason: {idea.reason}"
        try:
            result = await Runner.run(web_search_agent, input_data)
            return str(result.final_output)
        except Exception as e:
            print(f"Search failed for {idea.query}: {e}")
            return None

# Create manager instances
manager = ShinanIntelligence()

@router.post("/query", response_model=str)
async def run(
    request: ShinanQuery, 
) -> str:
    """
    Main endpoint to process queries.
    """
    result = await manager.run(request.query)
    return result

# @router.post("/upload")
# async def run_upload(
#     file: UploadFile = File(...)
# ):
#     """Upload a PDF slide deck and extract images for analysis."""


