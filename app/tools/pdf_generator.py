# In app/tools/pdf_generator.py
from weasyprint import HTML, CSS

def create_pdf(html_content: str, css_content: str, pdf_path: str) -> bool:
    """Renders HTML and CSS content into a PDF file using WeasyPrint."""
    try:
        css = CSS(string=css_content)
        html = HTML(string=html_content, base_url='.')
        html.write_pdf(pdf_path, stylesheets=[css])
        print(f"✅ PDF successfully generated at: {pdf_path}")
        return True
    except Exception as e:
        print(f"❌ Error during PDF generation: {e}")
        return False
