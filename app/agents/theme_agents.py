from pydantic import BaseModel, Field
from typing import List
from google.adk.agents import LlmAgent
from google.adk.agents.readonly_context import ReadonlyContext
from app.schemas.ResumeSchemas import ResumeResponse
from app.schemas.CoverLetterSchemas import CoverLetterFull
import json

# --- Pydantic Output Schemas for Agent Communication ---

class Color(BaseModel):
    """Represents a single color in the theme palette."""
    role: str = Field(description="The role of the color (e.g., 'primary', 'accent', 'text-headings').")
    hex_code: str = Field(description="The hex code for the color (e.g., '#FFFFFF').")

class ThemeAnalysisOutputSchema(BaseModel):
    """The structured output of the creative director's analysis."""
    name: str = Field(description="A creative and memorable name for the theme (e.g., 'Monaco Professional', 'Odessa Creative').")
    description: str = Field(description="A detailed description of the theme's layout and aesthetic to be used for the theme package.")
    color_palette: List[Color] = Field(description="A list of colors with their roles and hex codes.")
    google_fonts: List[str] = Field(description="A list of suggested Google Font names (e.g., ['Lato', 'Roboto Slab']).")

class ThemeGenerationOutputSchema(BaseModel):
  """Structured output for a single themed document (Jinja2 + CSS)."""
  template: str = Field(description="Complete Jinja2 template. Use context root 'resume' or 'cover_letter'.")
  styles: str = Field(description="Complete CSS string (may include @import for Google Fonts).")

# --- Agent Definitions ---

# AGENT 1: The Creative Director / Brand Strategist
theme_analyst_agent = LlmAgent(
  model="gemini-2.5-flash",  # Multimodal model required
  name="theme_analyst_agent",
  description="Analyzes prompt + image to produce a design brief (colors, fonts, directions).",
  instruction=(
    "You are a senior Creative Director. Produce ONLY valid JSON with keys: name, description, "
    "resume_direction, cover_letter_direction, color_palette (object with primary, accent, text). "
    "Keep directions concise (2-8 sentences). Include Google Font names and optional @import string."
  ),
  output_schema=ThemeAnalysisOutputSchema,
  output_key="theme_brief",
)

# AGENT 2A: The Resume Template Developer
resume_schema_json = json.dumps(ResumeResponse.model_json_schema())
resume_theme_agent = LlmAgent(
  model="gemini-2.5-flash",
  name="resume_theme_agent",
  description="Generates a Jinja2 template + CSS for resume using ResumeResponse schema field names.",
  instruction=(
    "You are a resume template developer. Input: creative director JSON brief. Output: ONLY a JSON object with keys 'template' and 'styles'. "
    "The Jinja2 template must expect a single variable 'resume'. Use only field names from the following JSON Schema: \n" + resume_schema_json + "\n"
    "Rules: standard Jinja2 syntax, loops via {% for x in resume.experience %}. No proprietary placeholders. "
    "Include Google Fonts via @import if specified by the brief. Return ONLY valid JSON."
  ),
  output_schema=ThemeGenerationOutputSchema,
  output_key="resume_theme",
)

# AGENT 2B: The Cover Letter Template Developer
cover_schema_json = json.dumps(CoverLetterFull.model_json_schema())

def cover_letter_instruction_provider(context: ReadonlyContext) -> str:
    """InstructionProvider to bypass ADK template processing for Jinja2 examples."""
    return (
        "You are a cover-letter template developer. Input: creative director JSON brief. Output: ONLY JSON with keys 'template' and 'styles'. "
        "Template must expect variable 'cover_letter'. Use field names from JSON Schema below strictly: \n" + cover_schema_json + "\n"
        "Use {% for p in cover_letter.bodyParagraphs %}<p>{{ p }}</p>{% endfor %} for body paragraphs. Include @import for fonts if in brief. Return ONLY valid JSON."
    )

cover_letter_theme_agent = LlmAgent(
  model="gemini-2.5-flash",
  name="cover_letter_theme_agent",
  description="Generates a Jinja2 template + CSS for cover letter using CoverLetterFull schema field names.",
  instruction=cover_letter_instruction_provider,  # Function instead of string
  output_schema=ThemeGenerationOutputSchema,
  output_key="cover_letter_theme",
)
