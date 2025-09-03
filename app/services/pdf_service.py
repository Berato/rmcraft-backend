
from pypdf import PdfReader
from io import BytesIO

from app.schemas.ResumeSchemas import ResumeResponse
from app.workflows.resume.resume_creation_workflow import parse_resume_text_with_genai



def extract_text_from_pdf(pdf_content: bytes) -> ResumeResponse:
    """
    Extract text from a PDF file.
    """
    try:
        reader = PdfReader(BytesIO(pdf_content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return parse_resume_text_with_genai(text)
    except Exception as e:
        raise ValueError(f"Error extracting text from PDF: {str(e)}")
