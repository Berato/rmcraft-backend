from google.genai import types
import os
from pydantic import BaseModel, Field
from typing import List
from google.adk.agents import LlmAgent
try:
    from google.adk.agents.readonly_context import ReadonlyContext
except ImportError:
    if os.getenv('USE_MOCK_ADK', 'false').lower() == 'true':
        from app.mocks.mock_adk import ReadonlyContext
    else:
        raise
from google.adk.planners import BuiltInPlanner
from app.schemas.ResumeSchemas import ResumeResponse
from app.schemas.CoverLetterSchemas import CoverLetterFull
import json

# --- Pydantic Output Schemas for Agent Communication ---

class ThemeAnalysisOutputSchema(BaseModel):
    """The structured output of the creative director's analysis."""
    name: str = Field(
        description="A creative and memorable name for the theme (e.g., 'Monaco Professional', 'Odessa Creative')."
    )
    description: str = Field(
        description="A detailed description of the theme's layout and aesthetic to be used for the theme package."
    )
    # REWORKED: This is now a single string, formatted as a human-readable list.
    color_palette_description: str = Field(
        description="A markdown-formatted string describing the color palette (e.g., '- Primary: #1a73e8 (Vibrant Blue)\\n- Accent: #ffc107 (Warm Amber)')."
    )
    # REWORKED: This is now a single string.
    google_fonts_description: str = Field(
        description="A markdown-formatted string describing the font pairings (e.g., '- Headings: Oswald\\n- Body Text: Lato')."
    )
    # RETAINED: This is still very useful for the designer agent.
    font_import_url: str = Field(
        description="The complete Google Fonts @import URL for the selected fonts (e.g., '@import url(\"https://fonts.googleapis.com/...\");')."
    )
class ThemeGenerationOutputSchema(BaseModel):
  """Structured output for a single themed document (Jinja2 + CSS)."""
  template: str = Field(description="Complete Jinja2 template. Use context root 'resume' or 'cover_letter'.")
  styles: str = Field(description="Complete CSS string (may include @import for Google Fonts).")

# --- Agent Definitions ---

# First, ensure your NEW schema (with string fields) is defined and available
# from app.schemas import ThemeAnalysisOutputSchema

font_awesome_instructions="""
To use icons, include font awesome by following these steps. Ensure you search to get the latest version.
1. Include the Font Awesome CSS file in the <head> section of your HTML document:
```html
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0-beta3/css/all.min.css">
```
2. Use the appropriate Font Awesome classes to add icons to your elements. For example:
```html
<i class="fas fa-camera"></i>
```html
<i class="fas fa-camera"></i>
```
3. Customize the size and color of the icons using CSS:
```css
.fas {
    font-size: 24px;
    color: #333;
}
```
"""
theme_analyst_agent = LlmAgent(
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
    ),
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024
        )
    ),
  model="gemini-2.5-pro", # Set to your preferred model
  name="theme_analyst_agent",
  description="Analyzes a prompt and inspiration image to produce a detailed design brief.",
  instruction=(
      "## Persona ##"
      "\nYou are an expert Creative Director and Brand Strategist. Your role is to create a single, unified design brief in Markdown that two separate agents—a Resume Designer and a Cover Letter Designer—will use to create a matching set of documents."

      "\n\n## Goal ##"
      "\nYour goal is to analyze a user's text prompt and an inspiration image to create a comprehensive **Markdown Design Blueprint**. This document will serve as the master plan and single source of truth for the two developer agents that will execute your vision."

      "\n\n## Input ##"
      "\nYou will receive a text prompt and a visual inspiration image."

      "\n\n## Process ##"
      "\n1. **Analyze Inputs:** Analyze both the text prompt and the visual elements of the inspiration image (layout, typography, color, mood)."
      "\n2. **Synthesize Theme:** Based on your analysis, invent a creative and descriptive name for the theme and write a brief description."
      "\n3. **Define Visuals:** Extract the color palette and suggest Google Fonts, then format them as specified below."
      "\n4. **Articulate Directions:** Write two distinct sets of instructions for the developer agents."

      "\n\n## Output Instructions ##"
      "\nCRITICAL: Your final output MUST be a single, comprehensive Markdown document. Do not use JSON. You must use the exact headers and formatting shown below."
      
      "\n\n---"
      "\n\n# Theme Design Blueprint"
      
      "\n\n## Theme Name"
      "\n*A creative and memorable name for the theme (e.g., 'Monaco Professional', 'Odessa Creative').*"
      
      "\n\n## Theme Description"
      "\n*A detailed, one-paragraph description of the theme's layout and aesthetic.*"
      
      "\n\n## Color Palette"
      "\n*A markdown list of the color palette with roles, hex codes, and a brief description.*"
      "\n- **Primary:** #0A2... (Deep Navy)"
      "\n- **Accent:** #E6A... (Gold Foil)"
      "\n- **Background:** #FFFFFF (White)"
      "\n- **Text Primary:** #333333 (Charcoal)"
      "\n- **Text Secondary:** #555555 (Medium Gray)"
      
      "\n\n## Typography"
      "\n*A markdown list of the font pairings.*"
      "\n- **Headings:** Oswald"
      "\n- **Body:** Lato"
      
      "\n\n## CSS @import URL"
      "\n*The complete, ready-to-use Google Fonts URL for the CSS, inside a CSS code block.*"
      "\n```css"
      "\n@import url('[https://fonts.googleapis.com/css2?family=Oswald:wght@700&family=Lato:wght@400;700&display=swap](https://fonts.googleapis.com/css2?family=Oswald:wght@700&family=Lato:wght@400;700&display=swap)');"
      "\n```"
      
      "\n\n## Design Direction for Resume Agent"
    "\n*Your concise (2-8 sentences) instructions for the Resume Design Agent. Be specific about layout (e.g., two-column, header structure) and how to use the colors and fonts.*"
    "\n\nNote (PDF themes): If this theme will be rendered to PDF, explicitly state whether the output should be full-bleed (no page margins) or use a small safe padding. Also include guidance for avoiding awkward page breaks: require utility classes such as `header-and-next` and `section-keep` (which must default to `page-break-inside: avoid;` / `break-inside: avoid;`) to keep a header with the following section and to keep section headings with at least the first 2-3 bullets. If the header would otherwise appear alone on a page, recommend a small dynamic-scaling strategy (reduce font-size or vertical spacing in small steps, e.g., 2-3% per step up to ~6%) before allowing a page break."
      
      "\n\n## Design Direction for Cover Letter Agent"
      "\n*Your concise (2-8 sentences) instructions for the Cover Letter Design Agent. Ensure it visually complements the resume design.*"
  ),

  output_key="creative_director_brief",
)

# AGENT 2A: The Resume Template Developer
resume_schema_json = json.dumps(ResumeResponse.model_json_schema())

resume_theme_agent = LlmAgent(
  model="gemini-2.5-pro", # As requested, the model is unchanged.
  name="resume_theme_agent",
  description="Generates a Jinja2 template + CSS for a resume using ResumeResponse schema field names.",
  instruction=(
    "## Persona ##"
    "\nYou are a specialist UI developer and document designer with expertise in Jinja2 templating and print-focused CSS. You can make any printed document with HTML and CSS. Your job is to translate a creative director's design brief into functional, clean code for a PDF resume."

    "\n\n## Goal ##"
    "\nYour goal is to take a design brief (focusing primarily on instructions for resume design but using the other information provided as well) and generate a corresponding Jinja2 template and CSS stylesheet. The final output will be rendered into a **professional PDF document**, so all code must be optimized for a fixed page layout."

    # --- GUIDANCE SECTION RESTORED AND CORRECTED ---
    "\n\n## GUIDANCE FROM CREATIVE DIRECTOR  ##"
    "\n**Creative Brief:** "
    "\n{creative_director_brief}"
    
    # --- REFERENCE EXAMPLE GUIDANCE (NOT FULL CODE TO AVOID BRACE PARSING ISSUES) ---
    "\n\n## REFERENCE EXAMPLE: Well-Proportioned Resume ##"
    "\n**CRITICAL MEASUREMENTS FROM REFERENCE EXAMPLE:**"
    "\nA well-designed resume uses these exact specifications to prevent summary overflow:"
    "\n\n**HEIGHT PROPORTIONS (Letter size ~11in height):**"
    "\n- Header (name + contact): ~15% of page (~1.5-1.7in) - COMPACT"
    "\n- Summary: ~10-12% of page (~1.0-1.3in) - COMPACT & TIGHT"
    "\n- Experience: ~50-60% of page (~5.5-6.5in) - MAIN CONTENT"
    "\n- Skills: ~8-10% of page"
    "\n- Education: ~8-10% of page"
    "\n\n**SPACING SPECIFICATIONS:**"
    "\n1. Summary MUST be compact: 10pt font (NOT 14-16pt), 1.4 line-height (NOT 2.0), minimal margins (0.15in NOT 0.5in)"
    "\n2. Section headers: 11pt max (NOT 14-16pt)"
    "\n3. Body text: 9.5-10pt for print"
    "\n4. Margins between sections: 0.05-0.15in (NOT 0.3-0.5in)"
    "\n5. Summary does NOT get larger font than body text"
    "\n\n**STRUCTURE REQUIREMENTS:**"
    "\n- Header section separate from summary (do NOT bundle them with page-break-inside avoid)"
    "\n- Summary section separate from experience (each can break independently if needed)"
    "\n- Only wrap individual .experience-item with .section-keep class"
    "\n- Summary and Experience MUST appear on the same page"
    "\n\n**CSS EXAMPLE VALUES:**"
    "\n.summary-text: font-size 10pt, line-height 1.4, margin-bottom 0.15in, padding 0"
    "\n.section-title: font-size 11pt, margin-bottom 0.08in"
    "\n.header: padding-bottom 0.15in, margin-bottom 0.15in"
    "\nAll inter-section spacing: 0.1-0.15in maximum"
    "\n\n## Rules & Constraints ##"
    "\n1. **Template Context:** The Jinja2 template must expect a single context variable named `resume`."
    "\n2. **Schema Adherence:** You MUST use the exact field names from the `ResumeResponse` JSON Schema to access data. For example: `{{ resume.personalInfo.name }}` and `{% for job in resume.experience %}`."
    "\n3. **Google Fonts:** You MUST use the provided **CSS Import URL** at the top of your CSS."
    "\n4. **Syntax:** Use standard, valid Jinja2 syntax only."
    "\n5. **CRITICAL - SPACING & PROPORTIONS:** Follow these strict guidelines to prevent summary overflow:"
    "\n    - **Summary section MUST be compact**: Use 9.5-10pt font (NOT larger than body text), 1.3-1.4 line-height, max 0.15in margins"
    "\n    - **Section headers**: 11-12pt max (NOT 14-16pt)"
    "\n    - **Inter-section spacing**: 0.1-0.15in maximum (NOT 0.3-0.5in)"
    "\n    - **Header (name+contact)**: Target ~1.5-1.7in total height"
    "\n    - **Summary section**: Target ~1.0-1.3in total height for 4-5 sentences"
    "\n    - **CRITICAL**: Summary and Experience MUST appear on the same page. Do NOT create layouts that force summary alone on page 1"
    "\n6. **PDF & Print Design:** Your code is for a PDF, not a website. You MUST follow these print design best practices:"
    "\n    - **Units:** Prefer print-friendly units. Use `pt` for `font-size` and `line-height`. Use `in` (inches) or `cm` (centimeters) for `margin` and `padding`. If `px` is used for convenience, include a comment mapping it to an exact `pt` fallback. Avoid `rem`/`em` for critical vertical rhythm in print unless deterministic conversions to `pt` are provided."
    "\n    - **Layout:** Design for a fixed page size (e.g., A4 or Letter). Ensure content does not overflow the page boundaries."
    "\n    - **Page Breaks:** Use `page-break-inside: avoid;` ONLY on individual experience items (`<div class=\"experience-item\">`). Do NOT wrap summary+experience together. Use `orphans: 2; widows: 2;` on paragraphs and lists to avoid single-line fragments at page edges."
    "\n    - **Borderless / Full-bleed:** State whether the template expects true full-bleed (`@page { margin: 0; }`) or will simulate full-bleed with background elements plus a small safe padding (document the padding in a CSS comment, e.g., `/* simulated full-bleed: safe padding 0.25in */`)."
    "\n    - **Section separation:** Keep header separate from summary. Keep summary separate from experience. Only wrap `.experience-item` and `.section-keep` classes on individual job blocks."
    "\n    - **Dynamic scaling rule:** Provide a documented strategy for small dynamic adjustments before allowing a page break: reduce vertical spacing and font-size in small steps (2-3% per pass, not exceeding ~6% total), and name the exact selectors the renderer can tweak (for example `html { font-size: 0.98rem; } /* fallback for measured overflow */`)."
    "\n7. **Required Fields:** USE the contact_info and the name fields from the schema! Make sure to include all information like Name, Contact Information, Work Experience, Skills, Education, and Projects (if present)."
    "\n8. **Visual Appeal:** Make sure the resume is visually appealing and easy to read. Use consistent fonts, colors, and spacing throughout the document. However, 'visually appealing' does NOT mean 'excessive spacing' - compact professional layouts are more impressive."
    f"{font_awesome_instructions}"
    "\n\n## Output Instructions ##"
    "\nCRITICAL: Your final output must be a single, valid JSON object with two keys: `template` (a string containing the Jinja2 code) and `styles` (a string containing the CSS code). Do not include markdown fences, explanations, or any other text. Your entire response must start with `{` and end with `}`."

    "\n\n##Schema for the 'resume' Variable. NOTE: THESE NEED TO BE STRICTLY ADHERED TO. DEVIANCE WILL BREAK THE TEMPLATE. ##"
    f"\n```json\n{resume_schema_json}\n```"
),
  output_schema=ThemeGenerationOutputSchema,
  output_key="resume_theme",
)

# AGENT 2B: The Cover Letter Template Developer
cover_schema_json = json.dumps(CoverLetterFull.model_json_schema())

def cover_letter_instruction_provider(context: ReadonlyContext) -> str:
    """
    Dynamically generates the instruction prompt for the cover_letter_theme_agent.
    """
    return (
        "## Persona ##"
        "\nYou are a specialist document designer and Jinja2 templating expert. Your job is to translate a creative director's design brief into a functional and elegant theme for a professional cover letter."

        "\n\n## Goal ##"
        "\nYour goal is to take a JSON design brief and generate a corresponding Jinja2 template and CSS stylesheet. The final output will be rendered into a **professional PDF document**, so all code must be optimized for a fixed page layout."

        "\n\n## GUIDANCE FROM CREATIVE DIRECTOR (JSON BRIEF) ##"
        "\n**Creative Brief:** "
        "\n{creative_director_brief}"
        
        # --- REFERENCE EXAMPLE GUIDANCE (NOT FULL CODE TO AVOID BRACE PARSING ISSUES) ---
        "\n\n## REFERENCE EXAMPLE: Professional Cover Letter ##"
        "\n**CRITICAL SPECIFICATIONS FROM REFERENCE EXAMPLE:**"
        "\nA well-designed cover letter uses these specifications for proper layout and readability:"
        "\n\n**TYPOGRAPHY & SPACING:**"
        "\n- Font size: 11pt for body text (slightly larger than resume for readability)"
        "\n- Line height: 1.6 for comfortable reading of paragraph text"
        "\n- Paragraph spacing: 0.18in between paragraphs"
        "\n- Header padding: 0.2in bottom, 0.25in margin below border"
        "\n- Section titles: 16pt for recipient name/title"
        "\n\n**STRUCTURE REQUIREMENTS:**"
        "\n- Use .header-and-next wrapper to keep header with opening paragraph"
        "\n- Header and opening paragraph must use page-break-inside: avoid together"
        "\n- Body paragraphs flow naturally without forced page-break-inside on each one"
        "\n- Signature section gets extra top margin (0.3in)"
        "\n- Signature line: 1pt border-top, 2in width, 0.4in top margin"
        "\n\n**PAGE CONTROL:**"
        "\n- Use orphans: 2 and widows: 2 on paragraphs"
        "\n- Allow natural page breaks between body paragraphs"
        "\n- Only prevent breaks between header and opening"
        "\n\n**KEY TAKEAWAYS:**"
        "\n- Header and opening grouped to prevent orphaned header"
        "\n- Natural paragraph flow without excessive break prevention"
        "\n- Larger font (11pt) and spacing (1.6 line-height) for prose readability"
        "\n- Professional signature section with proper spacing"

        "\n\n## Rules & Constraints ##"
        "\n1. **Template Context:** The Jinja2 template must expect a single context variable named `cover_letter`."
  "\n2. **Schema Adherence:** You MUST use only the following fields from the Cover Letter JSON Schema when rendering the template (do not read or reference any other fields):"
  "\n    - `title` (Optional[str])"
  "\n    - `openingParagraph` (Optional[str])"
  "\n    - `bodyParagraphs` (List[str])  # each item is a simple string, not an object"
  "\n    - `companyConnection` (Optional[str])"
  "\n    - `closingParagraph` (Optional[str])"
  "\n\n  For example, to loop through body paragraphs you must use: `{% for p in cover_letter.bodyParagraphs %}<p>{{ p }}</p>{% endfor %}`. Do NOT attempt to access other fields or nested objects."
        "\n3. **Google Fonts:** You MUST use the provided **CSS Import URL** at the top of your CSS."
        "\n4. **Syntax:** Use standard, valid Jinja2 syntax only."
        "\n5. **CRITICAL - PDF & Print Design:** Your code is for a PDF, not a website. You MUST follow these print design best practices:"
    "\n    - **Units:** Prefer print-friendly units. Use `pt` for `font-size` and `line-height`. Use `in` (inches) or `cm` (centimeters) for `margin` and `padding`. If `px` is used for convenience, include a comment mapping it to an exact `pt` fallback. Avoid `rem`/`em` for critical vertical rhythm in print unless deterministic conversions to `pt` are provided."
        "\n    - **Layout:** Design for a fixed page size (e.g., A4 or Letter). The layout should visually match the corresponding resume theme."
    "\n    - **Borderless / Full-bleed:** State whether the cover letter expects true full-bleed (`@page { margin: 0; }`) or a simulated safe padding. If simulating, add a CSS comment documenting the safe padding used."
    "\n    - **Avoid isolated header/paragraph pages:** The generated template must include at least a `.header-and-next` wrapper and `.section-keep` utility classes. Ensure the cover letter header (title and contact line) stays with the opening paragraph; wrap them in containers that default to `page-break-inside: avoid` and `page-break-after: avoid`."
    "\n    - **Page Breaks:** Use `page-break-inside: avoid;` on paragraphs and offer orphan/widow rules (e.g., `orphans: 2; widows: 2;`)."
    "\n Make sure to include all information like Name and Contact Information."
    "If title is STRATEGIC COVER LETTER replace it with users name"
    f"{font_awesome_instructions}"
        "\n\n## Output Instructions ##"
        "\nCRITICAL: Your final output must be a single, valid JSON object with two keys: `template` (a string containing the Jinja2 code) and `styles` (a string containing the CSS code). Do not include markdown fences, explanations, or any other text. Your entire response must start with `{` and end with `}`."

        "\n\n## Reference Schema for the 'cover_letter' Variable.  ##"
        f"\n```json\n{cover_schema_json}\n```"
        "ONLY USE THE title, openingParagraph, bodyParagraphs, companyConnection, and closingParagraph fields from this schema! Nothing else. No userProfile for sure. No metadata"
    )
    
cover_letter_theme_agent = LlmAgent(
  model="gemini-2.5-pro",
  name="cover_letter_theme_agent",
  description="Generates a Jinja2 template + CSS for cover letter using CoverLetterFull schema field names.",
  instruction=cover_letter_instruction_provider,  # Function instead of string
  output_schema=ThemeGenerationOutputSchema,
  output_key="cover_letter_theme",
)  
  
structured_theme_analyst_agent = LlmAgent(
    model="gemini-2.5-flash-lite",
    name="structured_theme_analyst_agent",
    description="Analyzes a prompt and inspiration image to produce a structured JSON design brief.",
    instruction=(
       "## Generate Import URL ##"
       "Your job is honestly just to make a JSON object representation of design direction output"
       "\nDESIGN DIRECTION OUTPUT"
       "{creative_director_brief}"

        "\n\n## Output Instructions ##"
        "\nCRITICAL: Your final output MUST be a single, valid JSON object that strictly conforms to the `ThemeAnalysisOutputSchema`. Do not include any explanations, markdown formatting, or any text outside of the JSON object. Your entire response must start with `{` and end with `}`."
        f"\n\n## REQUIRED JSON SCHEMA ##\n```json\n{ThemeAnalysisOutputSchema.model_json_schema()}\n```"
    ),
    output_schema=ThemeAnalysisOutputSchema,
    output_key="theme_brief",
)


