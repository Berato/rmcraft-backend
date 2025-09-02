from pydantic import BaseModel, Field
from typing import List, Dict
from google.adk.agents import LlmAgent
from google.genai import types

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
    """The structured output for a single theme component. Maps directly to your Theme schema."""
    template: str = Field(description="A complete Jinja2 template string.")
    styles: str = Field(description="A complete CSS string to style the template.")

# --- Agent Definitions ---

# AGENT 1: The Creative Director / Brand Strategist
theme_analyst_agent = LlmAgent(
  model="gemini-2.5-flash", # Multimodal model is REQUIRED
  name="theme_analyst_agent",
  description="Analyzes a prompt and image to create a detailed design brief for a new theme.",
  instruction=(
    "You are an expert Brand Strategist. Analyze the user's text prompt and the "
    "provided inspiration image to create a cohesive brand identity for a resume and cover letter theme. "
    "Your response MUST be ONLY a valid JSON object. Invent a creative name and description for the theme. "
    "The output must match the ThemeAnalysisOutputSchema."
  ),
  output_schema=ThemeAnalysisOutputSchema,
  output_key="theme_brief",
)

# AGENT 2A: The Resume Template Developer
resume_theme_agent = LlmAgent(
  model="gemini-2.5-flash",
  name="resume_theme_agent",
  description="Generates a Jinja2 template and CSS for a RESUME based on a design brief.",
  instruction=(
    "You are a resume template developer. Using the provided design brief (layout, colors, fonts), "
    "create a professional Jinja2 template and CSS for a RESUME. The JSON structure has these fields: "
    "name, summary, contact_info (array with email, phone, linkedin, github, website), "
    "experiences (array with id, company, position, startDate, endDate, responsibilities), "
    "skills (array with id, name, level), projects (array with id, name, description, url), "
    "education (array with id, institution, degree, startDate, endDate). "
    "Use placeholders like `%%name%%`, `%%summary%%`, `%%contact_info[0].email%%`. "
    "For loops use `<!-- loop skills skill -->%%skill.name%%<!-- endloop -->`. "
    "Your response MUST be ONLY a valid JSON object."
  ),
  output_schema=ThemeGenerationOutputSchema,
  output_key="resume_theme",
)

# AGENT 2B: The Cover Letter Template Developer
cover_letter_theme_agent = LlmAgent(
  model="gemini-2.5-flash",
  name="cover_letter_theme_agent",
  description="Generates a Jinja2 template and CSS for a COVER LETTER based on a design brief.",
  instruction=(
    "You are a document designer. Using the provided design brief, create a Jinja2 template and CSS for a COVER LETTER. "
    "Use placeholders like `%%recipient.name%%` and `%%sender.name%%`. For the body, use a loop: "
    "`<!-- loop body_paragraphs paragraph --><p>%%paragraph%%</p><!-- endloop -->`. Your response MUST be ONLY a valid JSON object."
  ),
  output_schema=ThemeGenerationOutputSchema,
  output_key="cover_letter_theme",
)
