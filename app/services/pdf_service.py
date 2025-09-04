
from pypdf import PdfReader
from io import BytesIO


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract text from a PDF file and return the raw text.
    """
    try:
        reader = PdfReader(BytesIO(pdf_content))
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text.strip()
    except Exception as e:
        raise ValueError(f"Error extracting text from PDF: {str(e)}")
