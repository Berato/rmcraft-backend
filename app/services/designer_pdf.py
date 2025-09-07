"""Services for rendering themed resume & cover letter PDFs and uploading them.

This module intentionally stays framework-light so it can be imported in tests
without heavy side effects. Cloudinary upload failures do not raise; they log
and return None for the URL so callers can decide fallback behavior.
"""
from __future__ import annotations

from typing import Optional, Dict, Any
from jinja2 import Environment, select_autoescape
import tempfile
import os
import uuid

from app.schemas.theme import ThemeSchema
from app.tools.pdf_generator import create_pdf
from app.tools.file_uploader import upload_to_cloudinary


def _get_env() -> Environment:
    return Environment(autoescape=select_autoescape(["html", "xml"]))


def render_template_to_html(template_str: str, context: Dict[str, Any]) -> str:
    """Render a Jinja2 template string with provided context."""
    env = _get_env()
    template = env.from_string(template_str)
    return template.render(context)


def create_designed_pdfs(
    resume_obj: Dict[str, Any],
    cover_letter_obj: Dict[str, Any],
    theme: ThemeSchema,
    output_dir: Optional[str] = None,
    upload: bool = True,
) -> Dict[str, Optional[str]]:
    """Render resume & cover letter using theme templates, produce PDFs, optionally upload.

    Args:
        resume_obj: Dict matching ResumeResponse structure (loose tolerated).
        cover_letter_obj: Dict matching CoverLetterFull structure.
        theme: Combined ThemeSchema containing both templates.
        output_dir: Optional directory for generated PDFs (defaults to temp dir).
        upload: Whether to upload PDFs to Cloudinary.

    Returns:
        Dict with local paths and (optional) uploaded URLs.
    """
    out_dir = output_dir or tempfile.gettempdir()
    os.makedirs(out_dir, exist_ok=True)

    # 1) Render HTML from Jinja2 templates
    resume_html = render_template_to_html(theme.resume_template.template, {"resume": resume_obj})
    cover_html = render_template_to_html(theme.cover_letter_template.template, {"cover_letter": cover_letter_obj})

    # 2) Generate file paths
    resume_pdf_path = os.path.join(out_dir, f"resume_{uuid.uuid4().hex[:8]}.pdf")
    cover_pdf_path = os.path.join(out_dir, f"cover_{uuid.uuid4().hex[:8]}.pdf")

    # 3) Create PDFs
    resume_ok = create_pdf(resume_html, theme.resume_template.styles, resume_pdf_path)
    cover_ok = create_pdf(cover_html, theme.cover_letter_template.styles, cover_pdf_path)

    resume_url = cover_url = None
    if upload:
        if resume_ok:
            resume_url = upload_to_cloudinary(resume_pdf_path, public_id=f"designer/resume/{uuid.uuid4().hex}")
        if cover_ok:
            cover_url = upload_to_cloudinary(cover_pdf_path, public_id=f"designer/cover/{uuid.uuid4().hex}")

    return {
        "resume_pdf_path": resume_pdf_path,
        "cover_pdf_path": cover_pdf_path,
        "resume_url": resume_url,
        "cover_url": cover_url,
    }


def minimal_theme_for_testing() -> ThemeSchema:
    """Return a tiny ThemeSchema instance for unit tests (no external calls)."""
    from app.schemas.theme import ThemeTemplate

    return ThemeSchema(
        name="Test Theme",
        description="A minimal test theme",
        resume_template=ThemeTemplate(
            template="""
<div class='resume'>
  <h1>{{ resume.personalInfo.firstName }} {{ resume.personalInfo.lastName }}</h1>
  {% if resume.summary %}<p>{{ resume.summary }}</p>{% endif %}
  <ul>
  {% for exp in resume.experience %}
    <li>{{ exp.position }} @ {{ exp.company }}</li>
  {% endfor %}
  </ul>
</div>
""".strip(),
            styles="""@page { size: A4; margin: 1cm; } body { font-family: Arial; } .resume { font-size: 12px; }""",
        ),
        cover_letter_template=ThemeTemplate(
            template="""
<div class='cover-letter'>
  <h2>{{ cover_letter.title or 'Cover Letter' }}</h2>
  {% for p in cover_letter.bodyParagraphs %}<p>{{ p }}</p>{% endfor %}
</div>
""".strip(),
            styles="""body { font-family: Helvetica; } .cover-letter { font-size: 12px; }""",
        ),
    )
