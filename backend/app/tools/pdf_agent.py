from dis import Instruction
from agents import Agent, FileSearchTool, function_tool
from agents.model_settings import ModelSettings
from pydantic import BaseModel

from typing import List, Optional
import pymupdf
import pytesseract
from PIL import Image
import io

# Add a tool to extract the text from the PDF.
PDF_ANALYSIS_PROMPT = """
You are a multi-modal assistant with expertise in reading and interpreting PDF slides. You receive a document that has been processed with OCR — so you are given plain text content per page — but the original slides may have contained diagrams, charts, visual groupings, or layout elements that OCR alone cannot fully capture.

Your job is to interpret what each slide is trying to communicate, using the OCR'd text as a starting point, and also reasoning about the likely visual context of the slide.

## Your Tasks:
1. For each page:
   - Analyze the OCR'd `text_content`.
   - Infer structure, flow, or meaning that may have been present visually.
   - Generate a `multi_modal_analysis`: a clear explanation of what the slide is communicating, integrating visual intuition (e.g., headers, images, diagrams).
   - If the OCR is noisy or broken, try to reconstruct intended meaning.
   
2. For the entire document:
   - Based on all the page analyses, write an `overall_summary` explaining what this document is about.
   - Identify key themes, sections, arguments, or progression.

## Output format:
Return a completed `PDFAnalysis` object where each `PageAnalysis` includes a filled `multi_modal_analysis`, and the root has an `overall_summary`.

Be thoughtful, precise, and helpful. Assume the reader can’t see the slides — you are their eyes and mind.
"""


class PageAnalysis(BaseModel):
    """
    Analysis of a single PDF page.
    """

    page_number: int
    text_content: str
    multi_modal_analysis: str


class PDFAnalysis(BaseModel):
    """
    Complete analysis of a PDF document.
    """

    total_pages: int
    overall_summary: str
    page_analyses: List[PageAnalysis]


@function_tool
async def ocr_pdf(url) -> PDFAnalysis:
    """
    This function performs OCR on each page of the PDF and returns a PDFAnalysis object.
    Returns: PDFAnalysis
    """
    response = requests.get(url)
    pdf_document = pymupdf.open(stream=response.content, filetype="pdf")
    total_pages = len(pdf_document)
    pages_analysis = []

    for page_num in range(total_pages):
        page = pdf_document[page_num]
        pix = page.get_pixmap()
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        text_content = pytesseract.image_to_string(image)

        pages_analysis.append(PageAnalysis(
            page_number=page_num + 1,
            text_content=text_content,
            multi_modal_analysis="",  
        ))

    pdf_document.close()

    return PDFAnalysis(
        total_pages=total_pages,
        page_analyses=pages_analysis,
        overall_summary="",  
    )


pdf_agent = Agent(
    name="PDF Agent",
    instructions=PDF_ANALYSIS_PROMPT,
    model="o3-mini",
    tools=[ocr_pdf],
    model_settings=ModelSettings(tool_choice="required"),
    output_type=PDFAnalysis,
)