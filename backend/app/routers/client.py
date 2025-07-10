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
from re import search
from token import OP
import uuid
from typing import Any, AsyncIterator, Dict, List, Sequence, cast

from agents import mcp, exceptions
import fitz
from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse, PlainTextResponse
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

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())

# Create router
router = APIRouter(prefix="/client", tags=["client"])

# Create a context relevance checker as a custom output of the Verification Agent
async def _context_relevance(run_result: RunResult) -> str:
    """Custom output extractor for sub‑agents that returns a Verification."""
    if not run_result.final_output.is_relevant:
        return("The report is not relevant to the context. Please improve the report using the following suggestions: {run_result.final_output.improvement_suggestions}")
    else:
        return "The report is relevant to the context, return this."

# Query to the Shinan Client
class ShinanQuery(BaseModel):
    """A query to the Shinan client."""
    query: str

# Creating the Shinan Session Manager for data handling.
class ShinanSessionManager:
    def __init__(self) -> None:
        self.context : ShinanContext = ShinanContext(company="SoftBank", role="Intern", interests=["AI", "Strategy"])
        self.input_items : List[TResponseInputItem] = []

        self.text_ideas: TextSearchIdeas = TextSearchIdeas(ideas=[])
        self.analysis: Analysis = Analysis(
            ideas=MaterialSearchIdeas(ideas=[]), 
            insights=MaterialInsights(insights=[]) 
        )

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

    # --- Search ideas and analysis management ---
    def set_text_ideas(self, text_ideas : TextSearchIdeas) -> None:
        """Set the text search ideas for the session."""
        self.text_ideas = text_ideas

    def set_analysis(self, analysis : Analysis) -> None:
        """Set the material analysis for the session."""
        self.analysis = analysis
    
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
            ]
        )
        if response.output[-1].type == "message":
            for content in response.output[-1].content:
                if content.type == "text":
                    return content

    async def run_messages(self, request: ShinanQuery) -> str:
        self.session.add_input_items({"content": request.query, "role": "user"})
        trace_id = gen_trace_id()

        with trace("Shinan Intelligence Messaging", trace_id=trace_id):
            result = await Runner.run(messages_agent, input=self.session.get_input_items(), context=self.session.get_context())
        
        self.session.add_input_items({"content": result.final_output, "role": "bot"}) # type: ignore
        return str(result.final_output)

    async def run_query(self, request: ShinanQuery) -> AsyncIterator[str]:

        trace_id = gen_trace_id()
        with trace("Shinan Intelligence Text Workflow", trace_id=trace_id):
            
            # Generating search ideas 
            ideas_generator = self._generate_search_ideas(request.query, text_agent)
            async for ev in ideas_generator:
                yield ev
            ideas : TextSearchIdeas = self.session.text_ideas

            # Performing overall search with a streaming implementation
            research_generator = self._overall_search(ideas)
            async for ev in research_generator:
                yield ev
            
            # Adding original query of user, given above research.
            self.session.add_input_items({"content": request.query, "role": "user"})

            print(self.session.get_input_items())

            # Generating report
            report_generator = self._generate_report()
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
            raise 

        context_message : str = ""
        async for ev in result.stream_events():

            if ev.type == "raw_response_event" and isinstance(ev.data, ResponseTextDeltaEvent):
                continue

            elif ev.type == "run_item_stream_event":
                if ev.item.type == "tool_call_item":
                    yield f"UPDATE 背景を確認させていただきます。"
                    asyncio.sleep(1.0)

                elif ev.item.type == "tool_call_output_item":
                    """ 
                    Checking user context and company information for personalized response 

                    Yields: 
                        context_message
                    """
                    company, role, interests_str = ev.item.output
                    if not interests_str:
                        interests_formatted = ""
                    elif len(interests_str) == 1:
                        interests_formatted = interests_str[0]
                    else:
                        interests_formatted = ", ".join(interests_str[:-1]) + f", and {interests_str[-1]}"

                    context_message = (
                        f"UPDATE {company}で{role}としてお勤めで、{interests_formatted}にご興味があるのですね。承知しました!"
                    )
                    yield f"{context_message}"
                    ideas_generation_logger.info(context_message)

        await asyncio.sleep(1.0)
        yield "ご利用ありがとうございます。いくつかの検索アプローチを洗い出しました。"
        await asyncio.sleep(1.0)

        search_ideas = result.final_output_as(TextSearchIdeas)
        self.session.set_text_ideas(search_ideas)

        ideas = search_ideas.model_dump()

        # Format for sending as HTML bullet points
        message = "以下はアイデアをご提案いたします。\n\n"
        for idea in ideas['ideas']:
            message += (
                f"検索: {idea['query']}\n"
                f"理由: {idea['reasoning']}\n\n"
            )

        yield message
        self.session.set_input_items(result.to_input_list())

    async def _search(self, idea: TextSearchIdea, search_logger: logging.Logger) -> AsyncIterator[str]:
        """
        Search the web for a single given idea.
        """
        input_data = f"Search term: {idea.query}\nReason: {idea.reasoning}"
        search_logger.info(f"Starting search for idea: {idea.query}")

        try:
            async with MCPServerSse(
                name="Shinan MCP Vector Store",
                params={"url": "http://localhost:8080/sse"}
            ) as mcp_server:
                search_mcp_agent = search_agent.clone(mcp_servers=[mcp_server])
                result = Runner.run_streamed(
                    search_mcp_agent,
                    input_data,
                    context=self.context,
                    max_turns=5
                )
                search_logger.debug(f"Search agent initialized for query: {idea.query}")

                async for ev in result.stream_events():
                    if ev.type != "run_item_stream_event":
                        continue

                    if ev.item.type == "tool_call_item":
                        search_logger.info(f"Processing run_item_stream_event: {ev.item.raw_item.type}")

                        if getattr(ev.item.raw_item, "type", None) == "web_search_call":
                            action = getattr(ev.item.raw_item, "action", None)
                            if action and getattr(action, "type", None) == "search":
                                search_logger.info(f"Searching the web for: {getattr(action, 'query', '')}")
                                yield f"UPDATE {idea.query}をWEBで検索中..."
                                await asyncio.sleep(1.0)

                        elif getattr(ev.item.raw_item, "type", None) == "function_call":
                            update_messages = [
                                "UPDATE MCPを介してソフトバンクに関連する公開資料を検索します...",
                                "UPDATE ソフトバンクの公開資料をMCP経由で調査中です...",
                                "UPDATE MCPを使って関連するレポートを検索しています...",
                                "UPDATE MCP経由で最新のソフトバンク資料を取得中です..."
                            ]
                            if not hasattr(self, '_mcp_update_idx'):
                                self._mcp_update_idx = 0
                            msg = update_messages[self._mcp_update_idx % len(update_messages)]
                            self._mcp_update_idx += 1
                            yield msg
                            await asyncio.sleep(1.0)

                    elif ev.item.type == "message_output_item":
                        search_logger.info(f"Found {ev.item.raw_item}")

            search_result = result.final_output_as(str)

            # Add to input items.
            search_logger.info({"content": search_result, "role": "assistant"})
            self.session.add_input_items({"content": search_result, "role": "assistant"})

        except Exception as e:
            search_logger.error(f"Search failed for '{idea.query}': {e}.", exc_info=True)

    async def _overall_search(self, search_ideas: TextSearchIdeas) -> AsyncIterator[str]:
        """Search the web and the vector store sources for a given idea."""

        search_logger = logger.getChild("search")
        search_logger.info(f"Starting overall search with {len(search_ideas.ideas)} ideas")

        with custom_span("Search"):
            """ 
            Utilizing asyncio's Queue for rapid streaming capabilities and scalability. 
            """

            # Create async generators for each idea
            generators = [self._search(idea, search_logger) for idea in search_ideas.ideas]
            queue: asyncio.Queue[str | None] = asyncio.Queue()
            
            async def consume_generator(gen, gen_id: int):
                """
                Running search generators asynchronously in following tasks list.
                Puts in asyncio Queue.
                """
                search_logger.debug(f"Starting generator {gen_id}")
                try:
                    async for item in gen:
                        search_logger.info(f"Generator {gen_id} yielded item: {item}")
                        await queue.put(item)
                    search_logger.info(f"Generator {gen_id} completed successfully")
                except Exception as e:
                    search_logger.error(f"Error in generator {gen_id}: {e}", exc_info=True)
                finally:
                    search_logger.info(f"Generator {gen_id} finishing, putting None in queue")
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

        yield "検索を完了しました！今からリポートを作成いたします。"

    async def _generate_report(self) -> AsyncIterator[str]:
        """Generate a report from a query and search results."""

        report_logger = logger.getChild("report")
        logger.setLevel(logging.INFO)

        async with MCPServerSse(name="Shinan MCP Vector Store", params={"url": "http://localhost:8080/sse"}, cache_tools_list=True) as mcp_server:
            writer_mcp_agent = writer_agent.clone(mcp_servers=[mcp_server])
            result = Runner.run_streamed(writer_mcp_agent, input=self.session.get_input_items(), context=self.context)
        
            async for ev in result.stream_events():
                if ev.type == "run_item_stream_event":
                    await asyncio.sleep(1.0)

                    if ev.item.type == "tool_call_item":
                        report_logger.info(f"Processing run_item_stream_event: {ev.item.raw_item.type}")

                        if ev.item.raw_item.type == "web_search_call":
                            report_logger.info(f"Web search call action: {ev.item.raw_item.action.type}")

                            if ev.item.raw_item.action.type == "search":
                                report_logger.info(f"Searching the web for: {ev.item.raw_item.action.query}")
                                yield f"UPDATE {ev.item.raw_item.action.query}をWEBで検索中..." 

                        elif ev.item.raw_item.type == "function_call":
                            report_logger.info("MCP to access a vector store of SoftBank reports")
                            update_messages = [
                                "UPDATE MCPを介してソフトバンクに関連する公開資料を検索します...",
                                "UPDATE ソフトバンクの公開資料をMCP経由で調査中です...",
                                "UPDATE MCPを使って関連するレポートを検索しています...",
                                "UPDATE MCP経由で最新のソフトバンク資料を取得中です..."
                            ]
                            if not hasattr(self, '_mcp_update_idx'):
                                self._mcp_update_idx = 0

                            msg = update_messages[self._mcp_update_idx % len(update_messages)]
                            self._mcp_update_idx += 1
                            await asyncio.sleep(1.0)
                            yield msg


                    elif ev.item.type == "message_output_item":
                        yield ("UPDATE リポートを完成しました！")
                        await asyncio.sleep(2.0)
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
        with trace("Shinan Intelligence Material Workflow", trace_id=trace_id):
            # Generate search ideas and material analysis
            analysis: Analysis = await self._generate_search_ideas_material(material, material_agent)

            # Research web for search ideas
            articles: List[str] = await self._research_web(analysis.ideas)

            # Generate report
            report: str = await self._generate_report(search_results=articles, material_analysis=analysis.insights)

        return report

    async def _generate_search_ideas_material(self, material: list[TResponseInputItem], idea_agent: Agent) -> Analysis:
        try:
            result = await Runner.run(idea_agent, material, context=self.context)
            analysis = result.final_output_as(Analysis)

            self.session.set_analysis(analysis)
            self.session.set_input_items(result.to_input_list())

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
            search_result = str(result.final_output)
            self.session.add_input_items({"content": search_result, "role": "assistant"})
            return search_result
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
        result = await Runner.run(writer_agent_with_verifier, input=self.session.get_input_items(), context=self.context, max_turns=4)
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

async def png_to_material(upload_file: UploadFile) -> List[Dict[str, Any]]: 
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
    Access to web search and MCP tools.
    """
    manager = ShinanTextIntelligence(session=session)

    try:
        result = manager.run_query(request)
        return StreamingResponse(result, media_type="application/json")

    except asyncio.exceptions.CancelledError:
        return {"result": "Stopped"}
        
    except Exception as e:
        return {"result": f"Error: {str(e)}"}

@router.post("/messages")
async def run_messages(request: ShinanQuery):
    """
    Main endpoint to respond simply to queries in a text format.
    """
    manager = ShinanTextIntelligence(session=session)

    try:
        result = await manager.run_messages(request)
        return PlainTextResponse(result)

    except asyncio.exceptions.CancelledError:
        return {"result": "Stopped"}
        
    except Exception as e:
        return {"result": f"Apologies, but there is an error. {str(e)}"}

@router.post("/deep_research")
async def run_query_research(request: ShinanQuery):
    """
    Main endpoint to process queries in a text format via Deep Research API.
    API call to Responses API Deep Research functionality.
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