# Action Plan: Implement Advanced Agentic Designer PDF Feature

## Objective

Upgrade the existing application by implementing an advanced "designer resume" feature. This new workflow will:
1.  **Analyze Inspiration:** A new multimodal agent will accept a user's prompt and an optional inspiration image to generate a detailed design brief.
2.  **Generate a Theme:** A second agent will use the brief to generate a Jinja2 template and CSS, explicitly using Google Fonts for high-quality typography.
3.  **Render the PDF:** The theme and resume data will be rendered into a professional PDF using WeasyPrint.
4.  **Deliver via Cloud:** The final PDF will be uploaded to Cloudinary, and a secure URL will be returned.

---
### ✅ **Phase 1: Update Project Dependencies & Configuration**

This feature requires new libraries for cloud storage, design, and configuration management.

**Action:**
1.  Execute the following command in the project's root directory to add the required libraries using Poetry.

    ```bash
    # For design, PDF, and cloud functionality
    poetry add jinja2 weasyprint cloudinary python-dotenv
    ```
2.  Create a `.env` file in your project's root directory to securely store your Cloudinary credentials.

    ```
    # In .env
    CLOUDINARY_CLOUD_NAME="your_cloud_name"
    CLOUDINARY_API_KEY="your_api_key"
    CLOUDINARY_API_SECRET="your_api_secret"
    ```
---
### 🛠️ **Phase 2: Implement Core Tools**

These utilities provide foundational capabilities for PDF generation and file uploading.

#### **1. PDF Generation Utility (`app/tools/pdf_generator.py`)**
**Action:**
Ensure this file exists. It uses **WeasyPrint** to convert HTML and CSS into a PDF. Its excellent support for `@import` rules is critical for using Google Fonts.

```python
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
```

#### **2. File Uploader Utility (`app/tools/file_uploader.py`)**
**Action:**
Create a new utility for uploading the generated PDF to Cloudinary.

```python
# In app/tools/file_uploader.py
import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

def configure_cloudinary():
    """Configures the Cloudinary client with credentials from .env."""
    cloudinary.config(
        cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
        api_key=os.getenv("CLOUDINARY_API_KEY"),
        api_secret=os.getenv("CLOUDINARY_API_SECRET"),
        secure=True
    )

def upload_to_cloudinary(file_path: str, public_id: str) -> str | None:
    """Uploads a file to Cloudinary and returns its secure URL."""
    try:
        configure_cloudinary()
        upload_result = cloudinary.uploader.upload(
            file_path,
            public_id=public_id,
            resource_type="auto",
            overwrite=True
        )
        print(f"✅ File successfully uploaded to Cloudinary.")
        return upload_result.get('secure_url')
    except Exception as e:
        print(f"❌ Cloudinary upload failed: {e}")
        return None
```
---
### 🤖 **Phase 3: Define the Two-Stage Designer Agent Workflow**

This workflow splits the design process into two distinct agentic steps for better modularity and reliability: creative direction (briefing) and code generation (designing).

**Action:**
In your `strategic_resume_agent.py` file (or a dedicated `app/schemas/` file), define the Pydantic schemas for the agents' structured outputs. Then, define the agents themselves.

#### **1. Define Pydantic Output Schemas**
```python
# In your schemas file or at the top of strategic_resume_agent.py
from pydantic import BaseModel, Field
from typing import List, Dict

class DesignBriefOutputSchema(BaseModel):
    layout_description: str = Field(description="A detailed description of the resume layout (e.g., 'two-column, minimalist').")
    color_palette: Dict[str, str] = Field(description="A dictionary mapping color roles (e.g., 'primary', 'accent') to hex color codes.")
    google_fonts: List[str] = Field(description="A list of suggested Google Font names (e.g., ['Lato', 'Roboto Slab']).")
    design_prompt_for_developer: str = Field(description="A concise, regenerated prompt for the next agent to use.")

class DesignerAgentOutputSchema(BaseModel):
    jinja_template: str = Field(description="A complete Jinja2 template string for the resume.")
    css_styles: str = Field(description="A complete CSS string to style the resume.")
```

#### **2. Define the Agents**
```python
# In strategic_resume_agent.py, with your other agent definitions

# NEW AGENT 1: The Creative Director
brief_agent = LlmAgent(
  model="gemini-2.5-flash", # A multimodal model is REQUIRED for image analysis
  name="brief_agent",
  description="Analyzes a text prompt and an inspiration image to create a detailed design brief.",
  instruction=(
    "You are an expert Creative Director. Analyze the user's text prompt and the "
    "provided inspiration image. Generate a detailed, structured JSON design brief. "
    "This brief MUST include: a description of the layout, a color palette with hex codes "
    "extracted from the image, a list of specific Google Fonts that closely match "
    "the typography, and a final concise `design_prompt_for_developer` for the next agent."
  ),
  output_schema=DesignBriefOutputSchema,
  output_key="design_brief",
)

# NEW AGENT 2: The UI Developer
designer_agent = LlmAgent(
  model="gemini-2.5-flash",
  name="designer_agent",
  description="""Generates a Jinja2 template and CSS stylesheet based on a detailed design brief.
  DESIGN BRIEF:
  {design_brief}
  """,
  instruction=(
    "You are an expert front-end developer. Your task is to execute the provided "
    "JSON design brief to generate a Jinja2 template and the corresponding CSS. "
    "Use the layout, colors, and fonts from the brief to create the theme. "
    "Ensure you include the specified Google Fonts using an `@import` rule at the top of the CSS. "
    "Your response MUST be ONLY a valid JSON object containing 'jinja_template' and 'css_styles' keys."
  ),
  output_schema=DesignerAgentOutputSchema,
)
```
---
### 🔗 **Phase 4: Integrate and Orchestrate the Full Workflow**

Modify your main `strategic_resume_agent` function to incorporate the new agents, handle multimodal input, and call the uploader.

#### **1. Update the Sequential Agent Workflow**
**Action:**
In your `strategic_resume_agent.py` file, add the `brief_agent` and `designer_agent` to the `SequentialAgent`'s `sub_agents` list. The new sequence ensures the strategic content is generated first, then the design brief, and finally the theme code.

```python
# In strategic_resume_agent.py
# MODIFIED SequentialAgent
full_workflow = SequentialAgent(
  name="full_resume_workflow",
  sub_agents=[
      resume_analysis_agent,
      summary_agent,
      brief_agent,      # NEW agent in the sequence
      designer_agent
  ],
  description="Complete resume analysis, summary, creative brief, and design workflow."
)
```

#### **2. Update the Main Function Signature and Input**
**Action:**
The main function must now accept the new inputs (prompt and image). The `types.Content` object must be constructed with both text and image parts.

```python
# In strategic_resume_agent.py
# MODIFIED function signature
async def strategic_resume_agent(
    resume_id: str,
    job_description_url: str,
    design_prompt: str,
    inspiration_image_data: bytes,
    inspiration_image_mime_type: str
):
    # ... (chroma setup and other agent definitions remain the same) ...

    # MODIFIED content object for multimodal input
    content = types.Content(
        role='user',
        parts=[
            types.Part(text=(
                f"1. First, perform the strategic analysis for resume {resume_id} against job url {job_description_url}. "
                f"2. Next, using the inspiration image provided, create a design brief based on the following prompt: '{design_prompt}'. "
                f"3. Finally, generate the Jinja2 and CSS theme based on the brief you created."
            )),
            types.Part(inline_data=types.Blob(
                mime_type=inspiration_image_mime_type,
                data=inspiration_image_data
            ))
        ]
    )
    # ... (runner setup remains the same) ...
```

#### **3. Update the Final Orchestration Logic**
**Action:**
After the `runner` loop, modify the logic to use the agent outputs to generate the PDF and upload it.

```python
# In strategic_resume_agent.py, AFTER the 'async for event in runner.run_async(...)' loop

from app.tools.pdf_generator import create_pdf
from app.tools.file_uploader import upload_to_cloudinary
from jinja2 import Environment
import uuid # Ensure uuid is imported

# The final_response dictionary is built inside the loop as before.
# It will now contain keys from all agents, including `design_brief`, `jinja_template`, etc.

jinja_template_str = final_response.get("jinja_template")
css_styles_str = final_response.get("css_styles")

if jinja_template_str and css_styles_str:
    print("🎨 Designer agent output found. Rendering and uploading PDF...")

    # 1. Render HTML from Jinja2 Template
    env = Environment()
    template = env.from_string(jinja_template_str)
    # The 'final_response' dict itself is the context for rendering
    html_output = template.render(final_response)

    # 2. Generate PDF locally (e.g., in a temporary directory)
    local_pdf_path = f"/tmp/Designed_Resume_{resume_id}_{uuid.uuid4().hex[:8]}.pdf"
    pdf_created = create_pdf(html_output, css_styles_str, local_pdf_path)

    # 3. Upload PDF to Cloudinary
    if pdf_created:
        public_id = f"resumes/{resume_id}/{uuid.uuid4().hex}"
        cloudinary_url = upload_to_cloudinary(local_pdf_path, public_id)
        final_response["cloudinary_url"] = cloudinary_url
else:
    print("⚠️ Designer agent output not found. Skipping PDF generation and upload.")
    final_response["cloudinary_url"] = None

# Return the full dictionary, which now includes the Cloudinary URL
return final_response
```