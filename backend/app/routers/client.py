import asyncio
import base64
import io
import uuid

from typing import List, Optional, Dict, Any, Sequence, AsyncIterator

import fitz
from PIL import Image
import pytesseract

from redis.asyncio import Redis

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends
from fastapi.responses import StreamingResponse
from starlette.status import HTTP_400_BAD_REQUEST
from pydantic import BaseModel

from agents import (
    Agent,
    InputGuardrailTripwireTriggered,
    Runner,
    RunResult,
    RunConfig,
    TResponseInputItem,
    custom_span,
    gen_trace_id,
    trace,
    MessageOutputItem,
    ToolCallItem,
    HandoffOutputItem,
    ToolCallOutputItem,
)
from agents.extensions.visualization import draw_graph
from agents.items import ItemHelpers, TResponse
from tools.idea_generation.material_idea_agent import (
    material_agent,
    MaterialInsightPoint,
    MaterialInsights,
    Analysis,
)
from tools.idea_generation.text_idea_agent import (
    text_agent,
    SearchIdea,
    SearchIdeas,
)
from tools.idea_generation.deep_research_agents import (
    assistant_agent, instruction_agent, clarifying_agent, triage_agent
)

from tools.research.web_search_agent import web_search_agent
from tools.report_generation.writer_agent import writer_agent, Report
from tools.report_generation.verifier_agent import verifier_agent
from tools.simple.simple_agent import simple_agent, Response

from context import ShinanContext

router = APIRouter(prefix="/client", tags=["client"])

import json
# redis_client = Redis(host="localhost", port=6379, decode_responses=True)

class ShinanQuery(BaseModel):
    """A query to the Shinan client."""
    query: str

async def _context_relevance(run_result: RunResult) -> str:
    """Custom output extractor for sub‑agents that return an AnalysisSummary."""
    if not run_result.final_output.is_relevant:
        return("Report is not relevant to the context. Please improve the report using the following suggestions: {run_result.final_output.improvement_suggestions}")
    else:
        return "Report is relevant to the context, return this."

class ShinanSessionManager:
    def __init__(self) -> None:
        self.context : ShinanContext = None
        self.input_items : List[TResponseInputItem] = []
        self.agents : ListAgent[ShinanContext] = [triage_agent]

    def get_context(self) -> ShinanContext:
        return self.context
    
    def set_context(self, context : ShinanContext):
        self.context = context

    # Handling inputs. Moving to Redis later.
    def get_input_items(self) -> List[TResponseInputItem]:
        return self.input_items

    def set_input_items(self, input_items : List[TResponseInputItem]):
        self.input_items = input_items

    # Handling agents. Moving to Redis later.
    def get_agent(self, index : int = -1) -> Agent[ShinanContext]:
        return self.agents[index]

    def add_agent(self, current_agent : Agent[ShinanContext]):
        self.agents.append(current_agent)

    def to_dict(self) -> dict:
        """Serialize to dict for Redis storage later"""
        return {
            "context": self.context.model_dump(),
            "input_items": [item.model_dump() if hasattr(item, 'model_dump') else item for item in self.input_items],
            "current_agent": self.current_agent.name if hasattr(self.current_agent, 'name') else str(self.current_agent)
        }
            
class ShinanTextIntelligence:
    """A class that orchestrates the text-based flow of Shinan Intelligence."""
    
    def __init__(self, session: ShinanSessionManager, conversation_id) -> None:
        self.session = session
        self.group_id = conversation_id

    @property
    def context(self) -> ShinanContext:
        return self.session.get_context()
            
    async def run_deep_research(self, query: str) -> AsyncIterator[str]:
        """
        Runs deep research logic and yields agent output as a stream.
        """
        self.session.set_input_items([{"content": query, "role": "user"}])

        with trace("Shinan Text Intelligence Deep Research", group_id=self.group_id):
            result = await Runner.run(
                starting_agent=self.session.get_agent(), 
                input=self.session.get_input_items(),
                context=self.context)

            for new_item in result.new_items:
                agent_name = new_item.agent.name

                if isinstance(new_item, MessageOutputItem):
                    yield f"data: {agent_name}: {ItemHelpers.text_message_output(new_item)}\n\n"
                elif isinstance(new_item, HandoffOutputItem):
                    yield f"data: Handed off from {new_item.source_agent.name} to {new_item.target_agent.name}\n\n"
                elif isinstance(new_item, ToolCallItem):
                    yield f"data: {agent_name}: Calling a tool\n\n"
                elif isinstance(new_item, ToolCallOutputItem):
                    yield f"data: {agent_name}: Tool call output: {new_item.output}\n\n"
                else:
                    yield f"data: {agent_name}: Skipping item: {new_item.__class__.__name__}\n\n"

                if agent_name == "Research Agent":
                    graph_data = draw_graph(self.session.get_agent(index=0))
                    yield f"data: graph: {json.dumps(graph_data)}\n\n"

        # Update session state
        self.session.set_input_items(result.to_input_list())
        self.session.add_agent(result.last_agent)

    async def run_query(self, query: str) -> AsyncIterator[str]:
        trace_id = gen_trace_id()
        with trace("Shinan Intelligence Text Workflow", trace_id=trace_id):
            # Generate search ideas
            ideas: SearchIdeas = await self._generate_search_ideas(query, text_agent)
            yield "Ideas have been generated."

            # Research web for search ideas
            articles: List[str] = await self._research_web(ideas)
            yield "Researching those ideas now."

            # Generate report
            report: Report = await self._generate_report(query=query, search_results=articles)
            yield f"{str(report.report)}"

    async def _generate_search_ideas(self, query: str, idea_agent: Agent) -> SearchIdeas:
        result = await Runner.run(idea_agent, query, context=self.context)
        return result.final_output_as(SearchIdeas)

    async def _search(self, idea: SearchIdea) -> str | None:
        """Search the web for a given idea."""

        print(f"Searching: {idea.query} - {idea.reasoning}")
        input_data = f"Search term: {idea.query}\nReason: {idea.reasoning}"
        try:
            result = await Runner.run(web_search_agent, input_data, context=self.context)
            return str(result.final_output)
        except Exception as e:
            print(f"Search failed for {idea.query}: {e}")
            return None

    async def _research_web(self, search_ideas: SearchIdeas) -> Sequence[str]:
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

    async def _generate_report(self, query: str, search_results: Sequence[str]) -> Report:
        """Generate a report from a query and search results."""

        verifier_tool = verifier_agent.as_tool(
            tool_name="verifier",
            tool_description="Use to verify the report is relevant to the context.",
            custom_output_extractor=_context_relevance,
        )
        writer_agent_with_verifier = writer_agent.clone(tools=[verifier_tool])
        result = await Runner.run(writer_agent_with_verifier, f"Query: {query}\nSearch results: {search_results}", context=self.context,)

        return result.final_output_as(Report)

class ShinanMaterialIntelligence:
    """A class that orchestrates the material-based flow of Shinan Intelligence."""
    
    def __init__(self, session: ShinanSessionManager, conversation_id) -> None:
        self.session = session
        self.group_id = conversation_id

    async def run_upload(self, material: List[dict]) -> str:
        with trace("Shinan Intelligence Material Workflow", group_id = self.group_id):
            # Generate search ideas and material analysis
            analysis: Analysis = await self._generate_search_ideas_material(material, material_agent)
            yield "Thinking about things"

            ideas : SearchIdeas = analysis.ideas
            insights : MaterialInsights = analysis.insights

            # Research web for search ideas
            articles: List[str] = await self._research_web(ideas)
            yield "Researching those ideas now."

            # Generate report
            report: Report = await self._generate_report(search_results=articles, material_analysis=insights)
            yield f"{str(report.report)}"

    async def _generate_search_ideas_material(self, material: list[dict], idea_agent: Agent) -> Analysis:
        try:
            result = await Runner.run(idea_agent, material, context=self.context)
            return result.final_output_as(Analysis)

        except InputGuardrailTripwireTriggered as e:
            print(f"Input guardrail triggered: {e}")
            raise HTTPException(
                status_code=400,
                detail="The provided material contains sensitive content that cannot be processed. Please review and remove any sensitive information before resubmitting."
            )

    async def _search(self, idea: SearchIdea) -> str | None:
        """Search the web for a given idea."""

        print(f"Searching: {idea.query} - {idea.reasoning}")
        input_data = f"Search term: {idea.query}\nReason: {idea.reasoning}"
        try:
            result = await Runner.run(web_search_agent, input_data, context=self.context)
            return str(result.final_output)
        except Exception as e:
            print(f"Search failed for {idea.query}: {e}")
            return None

    async def _research_web(self, search_ideas: SearchIdeas) -> Sequence[str]:
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

    async def _generate_report(self, search_results: Sequence[str], material_analysis: str) -> Report:
        """Generate a report from a query and search results."""

        verifier_tool = verifier_agent.as_tool(
            tool_name="verifier",
            tool_description="Use to verify the report is relevant to the context.",
            custom_output_extractor=_context_relevance,
        )
        writer_agent_with_verifier = writer_agent.clone(tools=[verifier_tool])
        result = await Runner.run(writer_agent_with_verifier, f"Material analysis: {material_analysis}\nSearch results: {search_results}", context=self.context)

        return result.final_output_as(Report)

session = ShinanSessionManager()

@router.post("/context")
async def set_context(request: ShinanContext):
    if not request.company or not request.role or request.interests is None:
        raise HTTPException(
            status_code=400,
            detail="company, role, and interests are required fields."
        )
    session.set_context(request)

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
        text_content = page.get_text()
        if text_content.strip():
            content_parts.append({
                "type": "input_text",
                "text": f"**Slide {page_num + 1} Text:**\n{text_content.strip()}\n"
            })
        
        # Convert to image
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
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
    
    return [
        {
            "role": "developer",
            "content": content_parts
        }
    ]

ALLOWED_TYPES = {"application/pdf": pdf_hybrid_to_material, "image/png": png_to_material, }

@router.post("/query")
async def run_query(
    request: ShinanQuery,
):
    """
    Main endpoint to process queries in a text format.
    """
    manager = ShinanTextIntelligence(session=session)

    try:
        result = manager.run_query(request.query)
        return StreamingResponse(result, media_type="application/json")

    except asyncio.exceptions.CancelledError:
        return {"result": "Stopped"}
        
    except Exception as e:
        return {"result": f"Error: {str(e)}"}

@router.post("/deep_research")
async def run_query_research(
    request: ShinanQuery,
):
    """
    Main endpoint to process queries in a text format via Deep Research.
    """
    manager = ShinanTextIntelligence(session=session, conversation_id = uuid.uuid4().hex[:16])

    try: 
        stream = manager.run_deep_research(request.query)   
        return StreamingResponse(stream, media_type="application/json")

    except asyncio.exceptions.CancelledError:
        return {"result": "Stopped"}
        
    except Exception as e:
        return {"result": f"Error: {str(e)}"}

@router.post("/upload")
async def run_upload(
    file: UploadFile = File(...), 
):
    """
    Main endpoint to process queries in a PDF or PNG format.
    """

    manager = ShinanMaterialIntelligence(context=context)

    processor = ALLOWED_TYPES.get(file.content_type)
    if not processor:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Only PDF and PNG are supported."
        )

    material = await processor(file)

    result = manager.run_upload(material)
    return StreamingResponse(result, media_type="application/json")