# Shinan Intelligence Client Router
# 
# This module provides the FastAPI router for handling client requests to the Shinan Intelligence system.
# It manages text-based queries, material uploads, and orchestrates the AI agent workflow.
#
# Author: Kushal Chattopadhyay

import asyncio
import base64
import io
import json
import logging
import os
import random
from token import OP
import uuid
from typing import Any, AsyncIterator, Dict, List, Sequence, cast

from agents import mcp
import fitz
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from PIL import Image
from openai.types.responses.response_item import McpCall
import pytesseract
from pydantic import BaseModel
from redis.asyncio import Redis
from starlette.status import HTTP_400_BAD_REQUEST

from agents import (
    Agent,
    HandoffOutputItem,
    InputGuardrailTripwireTriggered,
    MessageOutputItem,
    Runner,
    RunResult,
    RunResultStreaming,
    TResponseInputItem,
    ToolCallItem,
    ToolCallOutputItem,
    custom_span,
    gen_trace_id,
    trace,
)
from agents.extensions.visualization import draw_graph
from agents.items import ItemHelpers, TResponse, TResponseOutputItem
from agents.mcp import MCPServer, MCPServerSse
from context import ShinanContext
from openai.types.responses import (
    ResponseOutputMessage,
    ResponseOutputRefusal,
    ResponseOutputText,
    ResponseTextDeltaEvent,
)
from tools.idea_generation.material_idea_agent import (
    MaterialSearchIdea,
    MaterialSearchIdeas,
    MaterialInsightPoint,
    MaterialInsights,
    Analysis,
    material_agent
)
from tools.idea_generation.text_idea_agent import (
    TextSearchIdea,
    TextSearchIdeas,
    text_agent,
)
from tools.idea_generation.clarification_agent import (
    clarification_agent
)
from tools.report_generation.verifier_agent import verifier_agent
from tools.report_generation.writer_agent import Report, writer_agent, deep_research_agent
from tools.research.search_agent import search_agent
from tools.messages.messages_agent import messages_agent

from openai import OpenAI

logger = logging.getLogger("openai.agents")
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

router = APIRouter(prefix="/client", tags=["client"])

async def _context_relevance(run_result: RunResult) -> str:
    """Custom output extractor for sub‑agents that returns a Verification."""
    if not run_result.final_output.is_relevant:
        return("The report is not relevant to the context. Please improve the report using the following suggestions: {run_result.final_output.improvement_suggestions}")
    else:
        return "The report is relevant to the context, return this."

class ShinanQuery(BaseModel):
    """A query to the Shinan client."""
    query: str

class ShinanSessionManager:
    def __init__(self) -> None:
        # Session state initialization
        self.context : ShinanContext = ShinanContext(company="SoftBank", role="Intern", interests=["AI", "Strategy"])
        self.input_items : List[TResponseInputItem] = []
        self.agents : List[Agent[ShinanContext]] = []
        self.group_id = uuid.uuid4().hex[:16]

        self.text_ideas: TextSearchIdeas = TextSearchIdeas(ideas=[])
        self.analysis: Analysis = Analysis(
            ideas=MaterialSearchIdeas(ideas=[]), 
            insights=MaterialInsights(insights=[]) 
        )

        self.searches: List[str] = []
        self.report: Report = Report(report="")

    # --- Context management ---
    def get_context(self) -> ShinanContext:
        """Get the current session context."""
        return self.context
    
    def set_context(self, context : ShinanContext):
        """Set the session context."""
        self.context = context

    # --- Input item management ---
    def get_input_items(self) -> List[TResponseInputItem]:
        """Get the list of input items for the session."""
        return self.input_items

    def set_input_items(self, input_items : List[TResponseInputItem]) -> None:
        """Set the list of input items for the session."""
        self.input_items = input_items

    def add_input_items(self, input_item : TResponseInputItem) -> None:
        """Add a single input item to the session."""
        self.input_items.append(input_item)

    # --- Agent management ---
    def get_agent(self, index : int = -1) -> Agent[ShinanContext]:
        """Get an agent from the session by index (default: last)."""
        return self.agents[index]

    def add_agent(self, current_agent : Agent[ShinanContext]):
        """Add an agent to the session."""
        self.agents.append(current_agent)

    # --- Search ideas and analysis management ---
    def set_text_ideas(self, text_ideas : TextSearchIdeas) -> None:
        """Set the text search ideas for the session."""
        self.text_ideas = text_ideas

    def set_analysis(self, analysis : Analysis) -> None:
        """Set the material analysis for the session."""
        self.analysis = analysis

    # --- Search results management ---
    def get_searches(self) -> List[str]:
        """Get an agent from the session by index (default: last)."""
        return self.searches

    def add_search(self, search : str) -> None:
        """Add a search result to the session."""
        self.searches.append(search)
    
    # --- Report management ---
    def set_report(self, report: Report) -> None:
        """Set the generated report for the session."""
        self.report = report
            
class ShinanTextIntelligence:
    """A class that orchestrates the text-based flow of Shinan Intelligence."""
    
    def __init__(self, session: ShinanSessionManager) -> None:
        self.session = session

    @property
    def context(self) -> ShinanContext:
        return self.session.get_context()

    async def run_deep_research(self, request: ShinanQuery):
        system_message = """
            You are a professional researcher preparing a helpful, data-driven note on a company's current events in line with the user's queries.

            Do:
            - Focus on data-rich insights.
            - When appropriate, summarize data in a way that could be turned into charts or tables, and call this out in the response.
            - Prioritize reliable, up-to-date sources: blogs, articles, etc.
            - Include inline citations and return all source metadata.

            Be analytical, avoid generalities, and ensure that each section is helpful to the user's queries.
        """

        client = OpenAI(api_key = os.environ.get("OPENAI_API_KEY"))
        response = client.responses.create(
            model="o3-deep-research",
            input=[
                {
                "role": "developer",
                "content": [
                    {
                    "type": "input_text",
                    "text": system_message,
                    }
                ]
                },
                {
                "role": "user",
                "content": [
                    {
                    "type": "input_text",
                    "text": request.query,
                    }
                ]
                }
            ],
            reasoning={
                "summary": "auto"
            },
            tools=[
                {
                "type": "web_search_preview"
                },
                {
                "type": "mcp",
                "server_label": "file_research",
                "server_url": "https://localhost:8080/sse/",
                "require_approval": "never"
                }
            ]
        )
        if response.output[-1].type == "invalid_invalid_request_error":
            return "Due to verification constraints, this API call is currently unavailable."
        if response.output[-1].type == "message":
            for content in response.output[-1].content:
                if content.type == "text":
                    return content

    async def run_messages(self, request: ShinanQuery) -> str:
        self.session.add_input_items({"content": request.query, "role": "user"})
        trace_id = gen_trace_id()

        with trace("Shinan Intelligence Messaging", trace_id=trace_id, group_id=self.session.group_id):
            result = await Runner.run(messages_agent, input=self.session.get_input_items(), context=self.session.get_context())
        
        self.session.add_input_items({"content": request.final_output(), "role": "bot"}) # type: ignore
        return result.final_output()

    async def run_query(self, request: ShinanQuery) -> AsyncIterator[str]:

        self.session.set_input_items([{"content": request.query, "role": "user"}])
        trace_id = gen_trace_id()
        with trace("Shinan Intelligence Text Workflow", trace_id=trace_id, group_id=self.session.group_id):
            
            # Generating search ideas 
            ideas_generator = self._generate_search_ideas(request.query, text_agent)
            async for ev in ideas_generator:
                yield ev

            # Performing overall search with a streaming implementation
            ideas : TextSearchIdeas = self.session.text_ideas
            research_generator = self._overall_search(ideas)
            async for ev in research_generator:
                yield ev
            
            # Generating report
            searches = self.session.get_searches()

            report_generator = self._generate_report(query=request.query, search_results=searches)
            async for ev in report_generator:
                yield ev

    async def _generate_search_ideas(self, query: str, idea_agent: Agent) -> AsyncIterator[str]:
        """
        Generate search ideas from the given query using the specified idea agent.
        
        Args:
            query: The user's search query
            idea_agent: The agent responsible for generating search ideas
            
        Yields:
            JSON strings containing search ideas and context information
        """
        ideas_generation_logger = logger.getChild("idea_generation")

        try:
            result: RunResultStreaming = Runner.run_streamed(
                starting_agent=idea_agent, 
                input=query, 
                context=self.context
            )

        except Exception as e:
            ideas_generation_logger.error(f"Failed to initialize Runner: {e}")
            return

        context_message : str = ""
        async for ev in result.stream_events():

            if ev.type == "raw_response_event" and isinstance(ev.data, ResponseTextDeltaEvent):
                continue

            elif ev.type == "run_item_stream_event":
                if ev.item.type == "tool_call_item":
                    yield f"UPDATE Let me see who you are. Checking your context..."
                    await asyncio.sleep(1.0)

                if ev.item.type == "tool_call_output_item":
                    """ 
                    Checking user context and company information for personalized response 
                    Yields: context_message
                    """
                    company, role, interests_str = ev.item.output
                    if not interests_str:
                        interests_formatted = ""
                    elif len(interests_str) == 1:
                        interests_formatted = interests_str[0]
                    else:
                        interests_formatted = ", ".join(interests_str[:-1]) + f", and {interests_str[-1]}"

                    if interests_formatted:
                        context_message = (
                            f"UPDATE Got that you are a {role} at {company} "
                            f"and your interests include {interests_formatted}."
                        )
                    else:
                        context_message = f"UPDATE Got it! You are a {role} at {company}. "
                    yield f"{context_message}\nI'll align my responses with you!"

                    ideas_generation_logger.info(context_message)

        await asyncio.sleep(1.0)
        yield "Generated my ideas!"
        await asyncio.sleep(1.0)

        search_ideas = result.final_output_as(TextSearchIdeas)
        self.session.set_text_ideas(search_ideas)

        ideas = search_ideas.model_dump()

        # Format for sending as HTML bullet points
        message = "Here are some searches I am pursuing.\n\n"
        for idea in ideas['ideas']:
            message += (
                f"Query: {idea['query']}\n"
                f"Reason: {idea['reasoning']}\n\n"
            )

        yield message
        self.session.set_input_items(result.to_input_list())

    async def _search(self, idea: TextSearchIdea, search_logger: logging.Logger) -> AsyncIterator[str]:
        """Search the web for a given idea."""

        input_data = f"Search term: {idea.query}\nReason: {idea.reasoning}"
        search_logger.info(f"Starting search for idea: {idea.query}")
        
        try:
            async with MCPServerSse(name="Shinan MCP Vector Store", params={"url": "http://localhost:8080/sse"}) as mcp_server:
                search_mcp_agent = search_agent.clone(mcp_servers=[mcp_server])
                result = Runner.run_streamed(search_agent, input_data, context=self.context, max_turns=1)
                search_logger.debug(f"Search agent initialized for query: {idea.query}")

                # Add citation
                async for ev in result.stream_events():
                    if ev.type == "run_item_stream_event":

                        if ev.item.type == "tool_call_item":
                            search_logger.debug(f"Processing run_item_stream_event: {ev.item.raw_item.type}")

                            if ev.item.raw_item.type == "web_search_call":
                                search_logger.debug(f"Web search call action: {ev.item.raw_item.action.type}")

                                if ev.item.raw_item.action.type == "search":
                                    search_logger.debug(f"Searching the web for: {ev.item.raw_item.action.query}")
                                    yield f"UPDATE Searching the web for {idea.query}..." 
                                    await asyncio.sleep(1.0)

                                # elif ev.item.raw_item.action.type == "open_page":
                                #     search_logger.debug(f"Found website: {ev.item.raw_item.action.url}")
                                #     yield f"UPDATE Found this website at <link>{ev.item.raw_item.action.url}</link>. Opening it..."
                                #     await asyncio.sleep(1.0)

                        elif ev.item.type == "message_output_item":
                            search_logger.debug(f"Found {ev.item.raw_item}")
            
            search_result = result.final_output_as(str)
            self.session.add_search(search_result)
                
        except Exception as e:
            search_logger.error(f"Search failed for '{idea.query}': {e}", exc_info=True)

    async def _overall_search(self, search_ideas: TextSearchIdeas) -> AsyncIterator[str]:
        """Search the web and the vector store sources for a given idea."""

        search_logger = logger.getChild("search")
        search_logger.info(f"Starting overall search with {len(search_ideas.ideas)} ideas")

        with custom_span("Search"):
            # Create async generators for each idea
            generators = [self._search(idea, search_logger) for idea in search_ideas.ideas]
            queue: asyncio.Queue[str | None] = asyncio.Queue()
            
            async def consume_generator(gen, gen_id: int):
                search_logger.debug(f"Starting generator {gen_id}")
                try:
                    async for item in gen:
                        search_logger.debug(f"Generator {gen_id} yielded item: {item}")
                        await queue.put(item)
                    search_logger.debug(f"Generator {gen_id} completed successfully")
                except Exception as e:
                    search_logger.error(f"Error in generator {gen_id}: {e}", exc_info=True)
                finally:
                    search_logger.debug(f"Generator {gen_id} finishing, putting None in queue")
                    await queue.put(None)

            tasks = [
                asyncio.create_task(consume_generator(gen, i)) 
                for i, gen in enumerate(generators)
            ]
            search_logger.info(f"Created {len(tasks)} search tasks")
            
            try:
                finished = 0
                while finished < len(tasks):
                    item = await queue.get()
                    if item is None:
                        finished += 1
                        search_logger.debug(f"Generator finished, {finished}/{len(tasks)} complete")
                    else:
                        search_logger.debug(f"Yielding search result: {item}")
                        yield item
                search_logger.info("All search generators completed")
            finally:
                search_logger.debug("Cleaning up search tasks")
                for task in tasks:
                    if not task.done():
                        search_logger.debug(f"Cancelling task {id(task)}")
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                search_logger.info("All tasks gathered. Search workflow completed.")

        yield "I have all the information I need. Now I'll analyze my vector store of Softbank public intelligence!"

    async def _generate_report(self, query: str, search_results: List[str], is_deep_research: bool = False) -> AsyncIterator[str]:
        """Generate a report from a query and search results."""

        report_logger = logger.getChild("report")
        logger.setLevel(logging.INFO)

        verifier_tool = verifier_agent.as_tool(
            tool_name="verifier",
            tool_description="Use to verify the report is relevant to company, role, interests.",
            custom_output_extractor=_context_relevance,
        )
        
        async with MCPServerSse(name="Shinan MCP Vector Store", params={"url": "http://localhost:8080/sse"}, cache_tools_list=True) as mcp_server:
            writer_mcp_agent = writer_agent.clone(mcp_servers=[mcp_server])
            result = Runner.run_streamed(writer_mcp_agent, input=self.session.get_input_items(), context=self.context)
            async for ev in result.stream_events():
                if ev.type == "run_item_stream_event":
                    print(ev.item.type)

                    if ev.item.type == "tool_call_item":
                        report_logger.debug(f"Processing run_item_stream_event: {ev.item.raw_item.type}")

                        if ev.item.raw_item.type == "web_search_call":
                            report_logger.debug(f"Web search call action: {ev.item.raw_item.action.type}")

                            if ev.item.raw_item.action.type == "search":
                                report_logger.debug(f"Searching the web for: {ev.item.raw_item.action.query}")
                                yield f"UPDATE Searching the web for {ev.item.raw_item.action.query}..." 
                                await asyncio.sleep(1.0)

                        elif ev.item.raw_item.type == "function_call":
                            report_logger.debug(" MCP to access a vector store of SoftBank reports")
                            yield f"UPDATE Queried MCP to search a vector store of Softbank public files..."
                            await asyncio.sleep(1.0)

                    if ev.item.type == "message_output_item":
                        yield ("UPDATE Here's your report!")
                        await asyncio.sleep(1.0)

                        yield str(ItemHelpers.text_message_output(ev.item))

class ShinanMaterialIntelligence:
    """A class that orchestrates the material-based flow of Shinan Intelligence."""
    
    def __init__(self, session: ShinanSessionManager) -> None:
        self.session = session

    @property
    def context(self) -> ShinanContext:
        return self.session.get_context()

    async def run_upload(self, material: list[TResponseInputItem]) -> str:
        trace_id = gen_trace_id()
        with trace("Shinan Intelligence Material Workflow", trace_id=trace_id, group_id=self.session.group_id):
            # Generate search ideas and material analysis
            analysis: Analysis = await self._generate_search_ideas_material(material, material_agent)
            ideas : MaterialSearchIdeas = analysis.ideas
            insights : MaterialInsights = analysis.insights

            # Research web for search ideas
            articles: List[str] = await self._research_web(ideas)

            # Generate report
            report: str = await self._generate_report(search_results=articles, material_analysis=insights)

        return report

    async def _generate_search_ideas_material(self, material: list[TResponseInputItem], idea_agent: Agent) -> Analysis:
        try:
            result = await Runner.run(idea_agent, material, context=self.context)
            return result.final_output_as(Analysis)

        except InputGuardrailTripwireTriggered as e:
            print(f"Input guardrail triggered: {e}")
            raise HTTPException(
                status_code=400,
                detail="The provided material contains sensitive content that cannot be processed. Please review and remove any sensitive information before resubmitting."
            )

    async def _search(self, idea: MaterialSearchIdea) -> str | None:
        """Search the web for a given idea."""

        print(f"Searching: {idea.query} - {idea.reasoning}")
        input_data = f"Search term: {idea.query}\nReason: {idea.reasoning}"
        try:
            result = await Runner.run(search_agent, input_data, context=self.context)
            return str(result.final_output)
        except Exception as e:
            print(f"Search failed for {idea.query}: {e}")
            return None

    async def _research_web(self, search_ideas: MaterialSearchIdeas) -> List[str]:
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

    async def _generate_report(self, search_results: Sequence[str], material_analysis: MaterialInsights) -> str:
        """Generate a report from a query and search results."""

        verifier_tool = verifier_agent.as_tool(
            tool_name="verifier",
            tool_description="Use to verify the report is relevant to the context.",
            custom_output_extractor=_context_relevance,
        )
        writer_agent_with_verifier = writer_agent.clone(tools=[verifier_tool])
        result = await Runner.run(writer_agent_with_verifier, f"Material analysis: {material_analysis}\nSearch results: {search_results}", context=self.context)
        return result.final_output()

session = ShinanSessionManager()

async def pdf_hybrid_to_material(upload_file: UploadFile, max_pages: int = 10) -> List[Dict[str, Any]]:
    """
    Convert PDF to both text and images for comprehensive analysis
    
    Returns: 
        A list of dictionaries, each containing:
        - "type": "input_text" or "input_image"
        - "text": Text content if type is "input_text"
        - "image_url": Base64-encoded image data if type is "input_image"

    Example:
    [
        {
            "type": "input_text",
            "text": "I'm providing a slide deck. slide_deck.pdf (10 pages)\n\n"
        },
        {
            "type": "input_image",
            "image_url": "data:image/jpeg;base64,..."
        },
        ...
    ]
    """
    
    pdf_content = await upload_file.read()
    pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
    
    content_parts = [
        {
            "type": "input_text",
            "text": f"I'm providing a slide deck. {upload_file.filename} ({len(pdf_document)} pages)\n\n"
        }
    ]
    
    for page_num in range(len(pdf_document)):
        # Get the page
        page = pdf_document[page_num]
        
        # Extract text
        text_content = page.get_text() # type: ignore 
        if text_content.strip():
            content_parts.append({
                "type": "input_text",
                "text": f"**Slide {page_num + 1} Text:**\n{text_content.strip()}\n"
            })
        
        # Convert to image
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)) # type: ignore 
        img_data = pix.tobytes("png")
        base64_image = base64.b64encode(img_data).decode('utf-8')
        
        content_parts.append({
            "type": "input_image",
            "image_url": f"data:image/jpeg;base64,{base64_image}"
        })
        
        content_parts.append({
            "type": "input_text",
            "text": f"↑ Slide {page_num + 1} Visual\n---\n"
        })
    
    pdf_document.close()
    
    return [
        {
            "role": "user",
            "content": content_parts
        }
    ]

async def png_to_material(upload_file: UploadFile) -> list[TResponseInputItem]: 
    """
    Convert PNG to text (using OCR) and image for comprehensive analysis
    
    Returns: 
        A list of dictionaries, each containing:
        - "type": "input_text" or "input_image"
        - "text": OCR text content if type is "input_text"
        - "image_url": Base64-encoded image data if type is "input_image"

    Example:
    [
        {
            "type": "input_text",
            "text": "I'm providing an image. image.png\n\n"
        },
        {
            "type": "input_image",
            "image_url": "data:image/png;base64,..."
        },
        ...
    ]
    """
    
    # Read the PNG file
    image_content = await upload_file.read()
    
    image = Image.open(io.BytesIO(image_content))
    
    # Perform OCR to extract text
    try:
        ocr_text = pytesseract.image_to_string(image)
    except Exception as e:
        print(f"OCR failed: {e}")
        ocr_text = ""
    
    # Convert to base64 for image processing
    img_buffer = io.BytesIO()
    image.save(img_buffer, format='PNG')
    img_data = img_buffer.getvalue()
    base64_image = base64.b64encode(img_data).decode('utf-8')
    
    content_parts = [
        {
            "type": "input_text",
            "text": f"I'm providing an image. {upload_file.filename}\n\n"
        }
    ]
    
    # Add OCR text if available
    if ocr_text.strip():
        content_parts.append({
            "type": "input_text",
            "text": f"**Image Text (OCR):**\n{ocr_text.strip()}\n"
        })
    
    # Add the image
    content_parts.append({
        "type": "input_image",
        "image_url": f"data:image/png;base64,{base64_image}"
    })
    
    content_parts.append({
        "type": "input_text",
        "text": f"↑ Image Visual\n---\n"
    })
    
    raw_output = [
        {
            "role": "user",
            "content": content_parts
        }
    ]
    return raw_output # type: ignore

ALLOWED_TYPES = {"application/pdf": pdf_hybrid_to_material, "image/png": png_to_material, }

@router.post("/context")
async def set_context(context: ShinanContext):
    if not context.company or not context.role or context.interests is None:
        raise HTTPException(
            status_code=400,
            detail="company, role, and interests are required fields."
        )
    session.set_context(context)

@router.post("/query")
async def run_query(request: ShinanQuery):
    """
    Main endpoint to process queries in a text format.
    """
    manager = ShinanTextIntelligence(session=session)

    try:
        result = manager.run_query(request)
        return StreamingResponse(result, media_type="application/json")

    except asyncio.exceptions.CancelledError:
        return {"result": "Stopped"}
        
    except Exception as e:
        return {"result": f"Error: {str(e)}"}

@router.post("/messaging")
async def run_messages(request: ShinanQuery):
    """
    Main endpoint to process queries in a text format.
    """
    manager = ShinanTextIntelligence(session=session)

    try:
        result = await manager.run_messages(request)
        return result

    except asyncio.exceptions.CancelledError:
        return {"result": "Stopped"}
        
    except Exception as e:
        return {"result": f"Error: {str(e)}"}

@router.post("/deep_research")
async def run_query_research(request: ShinanQuery):
    """
    Main endpoint to process queries in a text format via Deep Research API.
    """
    manager = ShinanTextIntelligence(session=session)

    try: 
        stream = await manager.run_deep_research(request) 
        return stream  

    except asyncio.exceptions.CancelledError:
        return {"result": "Stopped"}
        
    except Exception as e:
        return {"result": f"Error: {str(e)}"}

@router.post("/upload")
async def run_upload(file: UploadFile = File(...)):
    """
    Main endpoint to process queries in a PDF or PNG format.
    """
    manager = ShinanMaterialIntelligence(session=session)
    content_type = file.content_type or ""
    processor = ALLOWED_TYPES.get(content_type)
    if not processor:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {content_type}. Only PDF and PNG are supported."
        )

    material = await processor(file)
    result = await manager.run_upload(material)
    return result