# Action Plan: Implement Advanced Agentic Designer PDF Feature

## Objective
    print("🎨 Designer agent output found. Rendering and uploading PDF...")
```markdown
# Designer Agent — Complete Implementation Plan

This document is the single authoritative plan and implementation guide for the "designer/theme" feature. It's written top-to-bottom so an LLM or engineer can implement the feature without further clarification. It uses the existing code where possible and lists precise files, function signatures, data shapes, tests, and verification steps.

Summary: build a stable pipeline that runs a Creative Director agent to produce design direction, then two template-generator agents that each produce strict JSON outputs containing Jinja2 templates + CSS that reference the exact variables defined by `CoverLetterFull.model_json_schema()` and `ResumeResponse.model_json_schema()`. Persist a Theme object containing both templates, render PDFs from theme + resume/cover letter data, upload PDFs to Cloudinary, and return download URLs.

---

## Goals / Acceptance Criteria

- There is a `Theme` model (Pydantic / Beanie style) that stores:
    - `name: str`
    - `description: str`
    - `resume_template: { template: str, styles: str }`
    - `cover_letter_template: { template: str, styles: str }`
    - `preview_urls` (optional) and timestamps
- Agents must output strict JSON only. They must be instructed to use the JSON schema examples provided by `CoverLetterFull.model_json_schema()` and `ResumeResponse.model_json_schema()` so variables in Jinja templates are exact matches.
- Templates must be valid Jinja2 and use the model fields directly (no custom placeholder syntax).
- A `create_designed_pdfs(resume_id, cover_letter_id, theme_id, db, output_dir=None)` function exists and:
    - fetches the resume and cover letter data objects
    - renders HTML from both templates with the correct context
    - creates PDFs using `app/tools/pdf_generator.create_pdf`
    - uploads PDFs via `app/tools/file_uploader.upload_to_cloudinary`
    - returns secure URLs and stores preview urls on the Theme (or ThemePackage)
- No regression: existing persisted theme pipeline (ADK runner -> save theme rows) remains functional. New changes extend it.

---

## High-level design (top-to-bottom)

1. Agent layer (ADK): three agents
     - `creative_director_agent` (analysis, design brief)
     - `resume_template_agent` (uses ResumeResponse.model_json_schema())
     - `cover_letter_template_agent` (uses CoverLetterFull.model_json_schema())
2. Runner orchestration: SequentialAgent(creative_director, ParallelAgent(resume_template_agent, cover_letter_template_agent))
3. Parse agent outputs (verify JSON only, validate against small Pydantic schemas)
4. Persist a `Theme` (Pydantic/Beanie) that contains both templates and styles
5. PDF renderer: `create_designed_pdfs(...)` to render + PDF + upload
6. Optional: Add an API endpoint to generate and return the PDFs on demand or serve stored URLs

---

## Files to add / modify (explicit)

- Modify: `app/agents/designer/Designer_Agent.md` (this file) — updated plan (current)
- Modify: `app/agents/theme_agents.py` — update instructions for the two template agents to include the exact JSON schema via `.model_json_schema()` and demand Jinja2 output.
- Add: `app/schemas/theme.py` — Pydantic models describing Theme and ThemeTemplate sub-objects (used for validation).
- Add or modify: `app/models/theme_beanie.py` (optional) — Beanie Document for Theme (if migrating to beanie) or update `app/models/theme.py` to include Pydantic/serializers for API.
- Modify: `app/services/theme_service.py` — add `save_theme_from_agents(final_response, db)` that accepts agent outputs, validates them, and persists them (reusing existing `create_theme` + `create_theme_package` where appropriate).
- Add: `app/services/designer_pdf.py` — implement `create_designed_pdfs(resume_id, cover_letter_id, theme_id, db, output_dir=None)`.
- Ensure `app/tools/pdf_generator.py` and `app/tools/file_uploader.py` match env var names and are tested.
- Tests: `tests/test_designer_agent.py`, `tests/test_designer_pdf.py`, and update integration test that calls theme flow.

---

## Concrete agent instructions (exact wording to embed in code)

Note: always include the model schema text inside the prompt to the agent by calling the model's `.model_json_schema()` at runtime and injecting it into the `instruction` field. Example: `ResumeResponse.model_json_schema()` or `CoverLetterFull.model_json_schema()`.

1) Creative Director agent (must be multimodal)

Instruction (string to pass to LlmAgent):

"""
You are a senior Creative Director and Brand Strategist. I will provide a textual brief and an optional inspiration image. Produce a single JSON object (no extra text) that follows this structure exactly:

{
    "name": "<creative theme name>",
    "description": "<1-2 paragraph description: layout, spacing, tone>",
    "resume_direction": "<explicit design instructions for resume templates, list of google fonts, FONTS_IMPORT string if needed>",
    "cover_letter_direction": "<explicit design instructions for cover letter templates, list of google fonts, FONTS_IMPORT string if needed>",
    "color_palette": {"primary":"#XXXXXX","accent":"#XXXXXX","text":"#XXXXXX"}
}

Constraints:
- Return only valid JSON, nothing else.
- Keep `resume_direction` and `cover_letter_direction` actionable and short (2-8 sentences each). Include exact Google Font names you want added, and provide an `@import` snippet or link for fonts.
"""

2) Resume template agent

Instruction (inject ResumeResponse.model_json_schema())

"""
You are a resume template developer. Input: a JSON design brief from a creative director. Output: a single JSON object ONLY, exactly with keys: `template` and `styles`.

The `template` must be a valid Jinja2 template that expects a single variable called `resume` whose structure exactly matches the following JSON Schema (use this to reference field names and types):

<INJECT ResumeResponse.model_json_schema() HERE>

Rules:
- Output MUST be valid JSON only.
- The Jinja2 template must use `resume` as the context root: e.g. `{{ resume.name }}`, `{{ resume.experiences[0].company }}`.
- Use standard Jinja2 loops and conditionals. NO custom placeholders.
- The `styles` value must be a complete CSS string. If you want Google Fonts, include an `@import` at the top of the CSS using the exact font names from the creative director.

Example minimal `template` snippet (NOT your output):
```
<div class="header">
    <h1>{{ resume.name }}</h1>
    <p>{{ resume.contact.email }}</p>
</div>
```

Return JSON structure:
{
    "template": "<JINJA_TEMPLATE_STRING>",
    "styles": "<CSS_STRING>"
}

"""

3) Cover letter template agent

Instruction (inject CoverLetterFull.model_json_schema())

"""
You are a cover-letter template developer. Input: the JSON design brief from the creative director. Output: a single JSON object ONLY with keys: `template` and `styles`.

The `template` must be valid Jinja2 and expect a single variable called `cover_letter` that follows the schema below:

<INJECT CoverLetterFull.model_json_schema() HERE>

Rules and constraints are the same as the resume agent: strict JSON only, standard Jinja2 syntax, `styles` must be valid CSS and may include `@import` Google Fonts generated by the creative director.

Return JSON:
{
    "template": "<JINJA_TEMPLATE_STRING>",
    "styles": "<CSS_STRING>"
}

---

## Pydantic / Beanie Theme model (recommended)

Add a Pydantic schema for validation and a Beanie Document for storage (or adapt to your SQLAlchemy models). Example Pydantic schema (`app/schemas/theme.py`):

```python
from pydantic import BaseModel
from typing import Optional

class ThemeTemplate(BaseModel):
        template: str
        styles: str

class ThemeSchema(BaseModel):
        name: str
        description: Optional[str]
        resume_template: ThemeTemplate
        cover_letter_template: ThemeTemplate
        # Optional preview URLs
        resume_preview_url: Optional[str]
        cover_letter_preview_url: Optional[str]

        class Config:
                orm_mode = True

```

If you adopt Beanie (MongoDB) create `app/models/theme_beanie.py`:

```python
from beanie import Document
from typing import Optional
from datetime import datetime
from app.schemas.theme import ThemeSchema, ThemeTemplate

class Theme(Document):
        name: str
        description: Optional[str]
        resume_template: ThemeTemplate
        cover_letter_template: ThemeTemplate
        resume_preview_url: Optional[str] = None
        cover_letter_preview_url: Optional[str] = None
        created_at: datetime = datetime.utcnow()
        updated_at: datetime = datetime.utcnow()

        class Settings:
                name = "themes"

        def to_schema(self) -> ThemeSchema:
                return ThemeSchema.from_orm(self)
```

If you remain on SQLAlchemy, update `app/models/theme.py` to store `template` and `styles` in `Text` columns and add JSON serializable helpers.

---

## Service: save and validate agent outputs

Add `app/services/theme_service.py` functions (or extend existing) with strict validation:

- `validate_and_build_theme_payload(final_response: dict) -> ThemeSchema` — validates agent outputs and builds ThemeSchema.
- `save_theme(theme_schema: ThemeSchema, db) -> Theme` — persists Theme; if using SQLAlchemy, reuse `create_theme` + `create_theme_package` but store the Jinja templates in `Text` fields.

Implementation notes:
- Validate that the agent outputs are JSON and match the schema shape.
- Reject responses that are not valid JSON (do not accept raw_response fallback for production).

---

## PDF generation & upload flow (detailed)

Add a new service `app/services/designer_pdf.py` with:

```python
from jinja2 import Environment, select_autoescape
from app.tools.pdf_generator import create_pdf
from app.tools.file_uploader import upload_to_cloudinary
import tempfile, os, uuid

def render_template_to_html(template_str: str, context: dict) -> str:
        env = Environment(autoescape=select_autoescape(['html', 'xml']))
        template = env.from_string(template_str)
        return template.render(context)

def create_designed_pdfs(resume_obj: dict, cover_letter_obj: dict, theme: ThemeSchema, output_dir: Optional[str]=None) -> dict:
        """
        Renders resume and cover letter to PDFs using the provided theme and returns local paths or upload URLs.
        """
        # 1) Render HTML
        resume_html = render_template_to_html(theme.resume_template.template, {'resume': resume_obj})
        cover_html = render_template_to_html(theme.cover_letter_template.template, {'cover_letter': cover_letter_obj})

        # 2) Create temp files and PDF
        out_dir = output_dir or tempfile.gettempdir()
        resume_pdf = os.path.join(out_dir, f"resume_{uuid.uuid4().hex[:8]}.pdf")
        cover_pdf = os.path.join(out_dir, f"cover_{uuid.uuid4().hex[:8]}.pdf")

        ok1 = create_pdf(resume_html, theme.resume_template.styles, resume_pdf)
        ok2 = create_pdf(cover_html, theme.cover_letter_template.styles, cover_pdf)

        # 3) Upload using Cloudinary and return URLs
        if ok1:
                resume_url = upload_to_cloudinary(resume_pdf, public_id=f"designer/resume/{uuid.uuid4().hex}")
        else:
                resume_url = None
        if ok2:
                cover_url = upload_to_cloudinary(cover_pdf, public_id=f"designer/cover/{uuid.uuid4().hex}")
        else:
                cover_url = None

        return {"resume_pdf": resume_pdf, "cover_pdf": cover_pdf, "resume_url": resume_url, "cover_url": cover_url}
```

Notes:
- WeasyPrint requires system packages (cairo, pango). Document this in README and CI.
- `upload_to_cloudinary` must read env vars exactly as used in this repo; see caveat below.

---

## Integration points with existing code

- `app/agents/theme_agents.py` — update agent `instruction` strings to inject `.model_json_schema()` for `ResumeResponse` and `CoverLetterFull`. Also change the output instruction to: "Return only JSON matching {your small Pydantic schema}."
- `app/features/theme_generator.py` — replace naive JSON parse/fallback behavior with strict validation and call `validate_and_build_theme_payload`.
- `app/tools/pdf_generator.py` & `app/tools/file_uploader.py` — confirm env var names and update to match `.env` keys (use `CLOUDINARY_CLOUD_NAME`, `CLOUDINARY_API_KEY`, `CLOUDINARY_API_SECRET`). Add graceful error messages.
- `app/services/theme_service.py` — add `save_theme_from_agents` wrapper that validates agent JSON and persists it as a `ThemeSchema` or SQL row.

---

## Tests to add

1. Unit test: `tests/test_theme_agent_output_validation.py`
     - given a representative JSON output from each agent, assert validation passes and invalid outputs fail.
2. Integration test: `tests/test_theme_generation_flow.py`
     - mock ADK Runner to return the creative director JSON + resume & cover templates. Assert `save_theme_from_agents` persists and returns a Theme.
3. PDF test: `tests/test_designer_pdf.py`
     - small fixture resume/cover objects and minimal templates/styles -> call `create_designed_pdfs` (mock Cloudinary) -> assert files created and mocked upload called.

---

## Edge cases & failure handling

- Agent returns non-JSON: treat as fatal for theme creation; log full text for debugging and return user-friendly error.
- Template renders raise errors (missing fields): validate templates by rendering once with a minimal fixture that includes all fields defined by the model schema; if render fails, reject agents' output and surface error for re-run.
- Long templates: persist in `Text` or Beanie Document field to avoid truncation.
- Cloudinary failure: return local PDF path and mark upload as failed, but do not delete the local PDF until manual cleanup.

---

## Devops / env / dependencies

- Add to poetry: `jinja2 weasyprint cloudinary python-dotenv beanie motor` (if you adopt Beanie)
- Document system deps for WeasyPrint in README: `libpango`, `libcairo`, `gdk-pixbuf`.
- `.env` keys expected:
    - CLOUDINARY_CLOUD_NAME
    - CLOUDINARY_API_KEY
    - CLOUDINARY_API_SECRET

---

## Migration notes (if using SQLAlchemy)

- Change `Theme.template` and `Theme.styles` columns to `Text` to store long templates and styles.
- Add optional `resume_preview_url` and `cover_letter_preview_url` string columns.

---

## Example call flow (end-to-end)

1. Client calls API / create-theme with `design_prompt` + `image`.
2. `app/features/theme_generator.create_and_save_theme` runs the Runner.
3. Agents produce validated JSON outputs and are converted to `ThemeSchema`.
4. Persist theme via `save_theme_from_agents`.
5. If the client requests 'render now', call `create_designed_pdfs(resume, cover, theme)` to create PDFs and upload.

---

## Quality gates & verification

- Unit tests green.
- Lint/formatting pass.
- Add a small smoke script `scripts/smoke_designer.py` to run a mock ADK flow locally using the repo's mock-adk (if available) and verify saved Theme + PDF creation.

---

## Final notes / decisions requested

When implementing, choose one of:
- Persist templates as-is and require agents to produce strict Jinja2 (recommended). This is simplest and lowest risk.
- Allow a custom placeholder syntax and add a translator -> more work and complexity.

If you want, I will implement the first coding step: update `app/agents/theme_agents.py` instructions to inject `.model_json_schema()` and make the agent outputs strict JSON, and update `app/tools/file_uploader.py` env var names. Otherwise this plan should serve as a perfect context for an LLM to implement the feature.

```
End of plan.
```

```}