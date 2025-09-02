# Action Plan: Implement Agentic Theme Generation Feature

## Objective

Integrate a new, modular feature for creating reusable design themes for resumes and cover letters. This feature will be exposed via a `POST /themes/create` endpoint that accepts a design prompt and an optional inspiration image. The workflow will use a sequence of ADK agents to analyze the design request and then generate the corresponding Jinja templates and CSS in parallel. The final output will be structured according to your existing `Theme` and `ThemePackage` Pydantic schemas and saved to the database.

---
### ✅ **Phase 1: Confirm Project Dependencies**

The required libraries (`jinja2`, `weasyprint`, `cloudinary`, `python-dotenv`) are already present in your `pyproject.toml`. No dependency changes are needed.

---
### 🤖 **Phase 2: Define the Theme Generation Agents and Schemas**

This feature requires three new specialized agents and their corresponding Pydantic output schemas, designed to be consistent with your existing schema definitions.

**Action:**
1.  Create a new file named `app/agents/theme_agents.py`.
2.  Add the following Pydantic schemas and ADK Agent definitions to the new file.

```python
# In app/agents/theme_agents.py

from pydantic import BaseModel, Field
from typing import List, Dict
from google.adk.agents import LlmAgent
from google.genai import types

# --- Pydantic Output Schemas for Agent Communication ---

class ThemeAnalysisOutputSchema(BaseModel):
    """The structured output of the creative director's analysis."""
    name: str = Field(description="A creative and memorable name for the theme (e.g., 'Monaco Professional', 'Odessa Creative').")
    description: str = Field(description="A detailed description of the theme's layout and aesthetic to be used for the theme package.")
    color_palette: Dict[str, str] = Field(description="A dictionary mapping color roles (e.g., 'primary', 'accent') to hex codes.")
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
    "create a professional Jinja2 template and CSS for a RESUME. The template should use placeholder "
    "variables consistent with the provided ResumeResponse schema (e.g., `{{ personalInfo.name }}`, `{% for job in experience %}`). Your response MUST "
    "be ONLY a valid JSON object containing 'template' and 'styles' keys."
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
    "You are a document designer. Using the provided design brief (layout, colors, fonts), "
    "create a professional Jinja2 template and CSS for a COVER LETTER. The template should use "
    "generic placeholders like `{{ recipient.name }}`, `{{ body_paragraphs }}`, and `{{ sender.name }}`. "
    "Your response MUST be ONLY a valid JSON object containing 'template' and 'styles' keys."
  ),
  output_schema=ThemeGenerationOutputSchema,
  output_key="cover_letter_theme",
)
```
---
### 🔗 **Phase 3: Construct the Full Agentic Workflow**

Combine the agents into a single, efficient workflow using ADK's `SequentialAgent` and `ParallelAgent`.

**Action:**
In a new orchestrator file, `app/features/theme_generator.py`, define the complete agentic graph.

```python
# In app/features/theme_generator.py

from google.adk.agents import SequentialAgent, ParallelAgent
from app.agents.theme_agents import theme_analyst_agent, resume_theme_agent, cover_letter_theme_agent

# Step 1: Define the parallel execution step for the two theme creators
parallel_theme_creation = ParallelAgent(
    name="parallel_theme_creation",
    description="Generates resume and cover letter themes concurrently.",
    sub_agents=[
        resume_theme_agent,
        cover_letter_theme_agent
    ]
)

# Step 2: Define the full sequential workflow
full_theme_workflow = SequentialAgent(
    name="full_theme_workflow",
    description="Analyzes a design request and then generates a complete theme package.",
    sub_agents=[
        theme_analyst_agent,
        parallel_theme_creation
    ]
)
```
---
### 🚀 **Phase 4: Create the Orchestrator and Database Logic**

This orchestrator function will run the agent workflow and then save the final, assembled theme package to your database using your existing schemas.

**Action:**
In the same `app/features/theme_generator.py` file, create the main orchestration function.

```python
# In app/features/theme_generator.py

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import uuid
# Import your actual database service functions and schemas
# from app.services.theme_service import create_theme, create_theme_package
# from app.schemas.ThemeSchemas import Theme, ThemePackage, ThemeType

async def create_and_save_theme(design_prompt: str, image_data: bytes, image_mime_type: str):
    """
    Orchestrates the end-to-end process of generating and saving a new theme.
    """
    # 1. Set up ADK Runner
    session_service = InMemorySessionService()
    session_id = uuid.uuid4().hex
    runner = Runner(agent=full_theme_workflow, session_service=session_service, app_name="theme_generator")

    # 2. Construct Multimodal Input
    content = types.Content(
        role='user',
        parts=[
            types.Part(text=design_prompt),
            types.Part(inline_data=types.Blob(mime_type=image_mime_type, data=image_data))
        ]
    )
    
    # 3. Execute the Workflow and Collect Results
    final_response = {}
    async for event in runner.run_async(new_message=content, session_id=session_id):
        if event.is_final_response() and event.output_key:
            final_response[event.output_key] = event.output.model_dump()

    # 4. Package the Theme and Save to Database
    theme_brief = final_response.get("theme_brief", {})
    resume_theme_data = final_response.get("resume_theme", {})
    cover_letter_theme_data = final_response.get("cover_letter_theme", {})

    if not all([theme_brief, resume_theme_data, cover_letter_theme_data]):
        raise Exception("Theme generation failed. One or more agents did not produce output.")

    # Create individual Theme records for resume and cover letter
    # This assumes a service function `create_theme` that returns the created Theme object
    
    # new_resume_theme = await create_theme(
    #     name=f"{theme_brief.get('name')} - Resume",
    #     description=theme_brief.get('description'),
    #     type=ThemeType.RESUME,
    #     template=resume_theme_data.get('template'),
    #     styles=resume_theme_data.get('styles')
    # )
    #
    # new_cover_letter_theme = await create_theme(
    #     name=f"{theme_brief.get('name')} - Cover Letter",
    #     description=theme_brief.get('description'),
    #     type=ThemeType.COVER_LETTER,
    #     template=cover_letter_theme_data.get('template'),
    #     styles=cover_letter_theme_data.get('styles')
    # )

    # Create the ThemePackage that links them
    # This assumes a service function `create_theme_package`
    
    # saved_theme_package = await create_theme_package(
    #     name=theme_brief.get('name'),
    #     description=theme_brief.get('description'),
    #     resume_template_id=new_resume_theme.id,
    #     cover_letter_template_id=new_cover_letter_theme.id
    # )
    #
    # return saved_theme_package
    
    # For now, we'll return a dictionary matching your ThemePackage schema
    print("✅ Theme package created successfully.")
    return {
        "name": theme_brief.get('name'),
        "description": theme_brief.get('description'),
        "resumeTemplate": resume_theme_data,
        "coverLetterTemplate": cover_letter_theme_data,
    }
```
---
### 🌐 **Phase 5: Implement the FastAPI Endpoint**

Finally, expose the entire feature through a new API endpoint, using your `ThemePackage` schema for the response model.

**Action:**
Create a new router file or add to an existing one to define the `/themes/create` endpoint.

```python
# In a new file, e.g., app/routers/themes.py
from fastapi import APIRouter, Body, UploadFile, File, status
from app.features.theme_generator import create_and_save_theme
from app.schemas.ThemeSchemas import ThemePackage # Import your actual schema

router = APIRouter(prefix="/themes", tags=["Themes"])

@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=ThemePackage)
async def create_theme_endpoint(
    design_prompt: str = Body(..., embed=True),
    inspiration_image: UploadFile = File(...)
):
    """
    Agentically generates and saves a new resume and cover letter theme
    based on a text prompt and an inspiration image.
    """
    image_data = await inspiration_image.read()
    image_mime_type = inspiration_image.content_type
    
    # The orchestrator runs the full workflow and returns an object matching the ThemePackage schema
    saved_theme = await create_and_save_theme(
        design_prompt=design_prompt, 
        image_data=image_data, 
        image_mime_type=image_mime_type
    )
    
    return saved_theme

# Remember to include this new router in your main FastAPI application instance.
```