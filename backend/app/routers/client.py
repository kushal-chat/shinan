import asyncio
from dataclasses import dataclass
from typing import Sequence, Optional, List, Dict, Any
import fitz
from PIL import Image
import base64
import logging
import io
import pytesseract

from fastapi import APIRouter, File, UploadFile, HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from pydantic import BaseModel
from agents import (
    Agent,
    InputGuardrailTripwireTriggered, 
    Runner, 
    RunResult,
    custom_span, 
    gen_trace_id, 
    trace,
)
from agents.mcp import MCPServer, MCPServerStreamableHttp
from agents.extensions.visualization import draw_graph

from tools.idea_generation.material_idea_agent import material_agent, MaterialInsightPoint, MaterialInsights, Analysis
from tools.idea_generation.text_idea_agent import text_agent, SearchIdea, SearchIdeas

from tools.web_search.web_search_agent import web_search_agent

from tools.report_generation.writer_agent import writer_agent, Report
from tools.report_generation.verifier_agent import verifier_agent

# Simple agent for testing.
from tools.simple.simple_agent import simple_agent, Response

from context import ShinanContext
from fastapi.responses import StreamingResponse
import json

router = APIRouter(prefix="/client", tags=["client"])

class ShinanQuery(BaseModel):
    """A query to the Shinan client."""
    query: str

class SimpleManager:
    """Initial test: A simple manager that runs a simple agent."""
    
    def __init__(self) -> None:
        pass

    async def run(self, query: str) -> Response:
        result = await Runner.run(simple_agent, query)
        return result.final_output_as(Response)

async def _context_relevance(run_result: RunResult) -> str:
    """Custom output extractor for sub‑agents that return an AnalysisSummary."""
    if not run_result.final_output.is_relevant:
        return("Report is not relevant to the context. Please improve the report using the following suggestions: {run_result.final_output.improvement_suggestions}")
    else:
        return "Report is relevant to the context, return this."
        
class ShinanTextIntelligence:
    """A class that orchestrates the text-based flow of Shinan Intelligence."""
    
    def __init__(self, context: ShinanContext) -> None:
        self.context = context

    async def run_query(self, query: str) -> str:
        trace_id = gen_trace_id()
        with trace("Shinan Intelligence Text Workflow", trace_id=trace_id):
            # Generate search ideas
            ideas: SearchIdeas = await self._generate_search_ideas(query, text_agent)

            # Research web for search ideas
            articles: List[str] = await self._research_web(ideas)

            # Generate report
            report: Report = await self._generate_report(query=query, search_results=articles)

        return str(report.report)

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
        result = await Runner.run(writer_agent_with_verifier, f"Query: {query}\nSearch results: {search_results}", context=self.context)

        return result.final_output_as(Report)

class ShinanMaterialIntelligence:
    """A class that orchestrates the material-based flow of Shinan Intelligence."""
    
    def __init__(self, context: ShinanContext) -> None:
        self.context = context

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

    async def run_upload(self, material: list[dict]) -> str:
        trace_id = gen_trace_id()
        with trace("Shinan Intelligence Material Workflow", trace_id=trace_id):
            # Generate search ideas and material analysis
            analysis: Analysis = await self._generate_search_ideas_material(material, material_agent)
            ideas : SearchIdeas = analysis.ideas
            insights : MaterialInsights = analysis.insights

            # Research web for search ideas
            articles: List[str] = await self._research_web(ideas)

            # Generate report
            report: Report = await self._generate_report(search_results=articles, material_analysis=insights)

        return str(report.report)

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

    async def _generate_report(self, search_results: Sequence[str], material_analysis: Optional[str] = None) -> Report:
        """Generate a report from a query and search results."""

        verifier_tool = verifier_agent.as_tool(
            tool_name="verifier",
            tool_description="Use to verify the report is relevant to the context.",
            custom_output_extractor=_context_relevance,
        )
        writer_agent_with_verifier = writer_agent.clone(tools=[verifier_tool])
        result = await Runner.run(writer_agent_with_verifier, f"Material analysis: {material_analysis}\nSearch results: {search_results}", context=self.context)

        return result.final_output_as(Report)

# Example context.
context = ShinanContext(
    company="",
    role="",
    interests=[]
)

@router.post("/context")
async def set_context(
    request: ShinanContext,
):
    """
    Set the context for the Shinan Intelligence.
    """
    global context
    context = request
    
    logging.info('Context set successfully')
    return {"result": "Context set successfully"}

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
            "role": "user",
            "content": content_parts
        }
    ]

ALLOWED_TYPES = {"application/pdf": pdf_hybrid_to_material, "image/png": png_to_material,}

@router.post("/query")
async def run_query(request: ShinanQuery):
    """
    Main endpoint to process queries in a text format.
    """
    manager = ShinanTextIntelligence(context=context)

    try:
        result = await manager.run_query(request.query)

        return {"result": result}

    except Exception as e:
        return {"result": f"Error: {str(e)}"}

@router.post("/upload")
async def run_upload(file: UploadFile = File(...)):
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
    result = await manager.run_upload(material)
    return result