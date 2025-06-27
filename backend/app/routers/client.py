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
    InputGuardrailTripwireTriggered, 
    Runner, 
    custom_span, 
    gen_trace_id, 
    trace,
)
from agents.mcp import MCPServer, MCPServerStreamableHttp

from tools.material_agent import material_agent
from tools.simple_agent import simple_agent, Response
from tools.idea_agent import idea_agent, Idea, Ideas
from tools.web_search_agent import web_search_agent
from tools.writer_agent import writer_agent, Report

from context import ShinanContext

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
    
    def __init__(self, context: ShinanContext) -> None:
        self.context = context

    async def _run_workflow(self, input_data, agent, is_material=False) -> str:
        trace_id = gen_trace_id()
        workflow_name = "Shinan Intelligence Material Workflow" if is_material else "Shinan Intelligence Text Workflow"
        with trace(workflow_name, trace_id=trace_id):
            # Generate search ideas
            if is_material:
                ideas: List[Idea] = await self._generate_search_ideas_material(input_data, agent)
            else:
                ideas: List[Idea] = await self._generate_search_ideas(input_data, agent)
            # Research web
            articles: List[str] = await self._research_web(ideas)
            # Generate report
            report: str = await self._generate_report(input_data, articles)
            return str(report.report)

    async def run_query(self, query: str) -> str:
        return await self._run_workflow(query, idea_agent, is_material=False)

    async def run_upload(self, material: list[dict]) -> str:
        return await self._run_workflow(material, material_agent, is_material=True)

    async def _generate_search_ideas(self, query: str, agent) -> Ideas:
        try:
            result = await Runner.run(agent, query, context=self.context)
            return result.final_output_as(Ideas)
        except InputGuardrailTripwireTriggered as e:
            print(f"There appears to be a sensitive input. {e}")
            return Ideas(ideas=[])

    async def _generate_search_ideas_material(self, material: list[dict], agent) -> Ideas:
        try:
            result = await Runner.run(agent, material, context=self.context)
            return result.final_output_as(Ideas)
        except InputGuardrailTripwireTriggered as e:
            print(f"There appears to be a sensitive input. {e}")
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

        print(f"Searching: {idea.query} - {idea.reasoning}")
        input_data = f"Search term: {idea.query}\nReason: {idea.reasoning}"
        try:
            result = await Runner.run(web_search_agent, input_data)
            return str(result.final_output)
        except Exception as e:
            print(f"Search failed for {idea.query}: {e}")
            return None

# Example context.

context = ShinanContext(
    company="SoftBank",
    role="Research Analyst",
    interests=["Diffusion Models", "Japan AI"],
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

manager = ShinanIntelligence(context=context)

@router.post("/query")
async def run_query(
    request: ShinanQuery, 
):
    """
    Main endpoint to process queries in a text format.
    """
    try:
        result = await manager.run_query(request.query)
        return {"result": result}

    except Exception as e:
        return {"result": f"Error: {str(e)}"}

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

ALLOWED_TYPES = {
    "application/pdf": pdf_hybrid_to_material,
    "image/png": png_to_material,
}

@router.post("/upload")
async def run_upload(file: UploadFile = File(...)):
    """
    Main endpoint to process queries in a PDF or PNG format.
    """

    processor = ALLOWED_TYPES.get(file.content_type)
    if not processor:
        raise HTTPException(
            status_code=HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. Only PDF and PNG are supported."
        )

    material = await processor(file)
    result = await manager.run_upload(material)
    return result