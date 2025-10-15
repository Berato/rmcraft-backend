# Agile User Story: Theme Triage Multi-Agent Workflow

## Story ID
`FEATURE-THEME-TRIAGE-001`

## Epic
Theme Quality Assurance & Automated Remediation

## User Story

**As a** theme administrator  
**I want** an intelligent agent-based workflow that can analyze PDF outputs from themes, identify design and layout flaws, and automatically fix the underlying theme code  
**So that** I can ensure all themes produce professional, well-formatted documents without manual code inspection

---

## Acceptance Criteria

1. ✅ Endpoint accepts `theme_id` (required) + optional `resume_pdf` and/or `cover_letter_pdf` file uploads
2. ✅ At least one PDF (resume or cover letter) must be provided, or the request fails with validation error
3. ✅ Multi-agent workflow correctly identifies issues in uploaded PDFs (layout problems, text breaks, formatting issues)
4. ✅ Agents map identified issues to specific problems in the theme code (Jinja2 templates and CSS)
5. ✅ Engineer agents generate fixes for all identified problems
6. ✅ Fixed theme code is saved to the database (updates the theme package)
7. ✅ Verification agent renders new PDFs and checks if fixes resolved original problems
8. ✅ Optional retry mechanism (max 3 attempts) if initial fixes don't resolve all issues
9. ✅ Response includes summary of problems found, fixes applied, and verification status
10. ✅ Response includes URLs to newly rendered PDFs for manual review

---

## Technical Context

### Relevant Repository Locations

#### Key Files to Create
- **New Agents File**: `/app/agents/triage/triage_agents.py`
- **New Workflow**: `/app/workflows/theme_triage_workflow.py`
- **New Endpoint**: `/app/api/v1/endpoints/themes.py` (add to existing router)
- **New Schemas**: `/app/schemas/triage_schemas.py`

#### Existing Files to Reference
- **Theme CRUD**: `/app/crud/crud_theme.py` - Database operations for themes
- **Theme Service**: `/app/services/theme_service.py` - Theme validation and persistence
- **PDF Service**: `/app/services/designer_pdf.py` - PDF rendering with WeasyPrint
- **Theme Documents**: `/app/schemas/theme_documents.py` - Beanie Document models
- **Existing Multi-Agent Example**: `/app/features/theme_generator.py` - Reference for ADK patterns
- **Resume Service**: `/app/services/resume_service.py` - Get resume for test rendering

### Technology Stack
- **Framework**: Google Agent Development Kit (ADK)
- **Agent Types**: `LlmAgent`, `ParallelAgent`, `SequentialAgent`
- **Models**: Gemini 2.5 Pro/Flash
- **PDF Rendering**: WeasyPrint
- **Database**: MongoDB via Beanie ODM
- **API Framework**: FastAPI

---

## Architecture Overview

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    THEME TRIAGE WORKFLOW                         │
└─────────────────────────────────────────────────────────────────┘

1. [VALIDATION] Check inputs (theme_id + at least one PDF)
          ↓
2. [FETCH] Get theme package from DB
          ↓
3. [CONDITIONAL ROUTING] Determine which PDFs were uploaded
          ↓
    ┌─────────────────────────────────────────┐
    │  Resume PDF Provided?  │  Cover Letter PDF Provided?
    └─────────────────────────────────────────┘
              ↓                        ↓
    ┌─────────────────┐      ┌─────────────────┐
    │  Resume Track   │      │ Cover Letter    │
    │                 │      │ Track           │
    └─────────────────┘      └─────────────────┘
              ↓                        ↓
4. [PARALLEL AGENT] Run 1-2 Sequential Sub-Workflows in Parallel
          ↓
    Each Sequential Sub-Workflow:
    ┌────────────────────────────────────────┐
    │  A. TRIAGE AGENT (Identify Issues)     │
    │     - Analyze PDF for visual problems  │
    │     - Map issues to theme code         │
    │     Output: List of issues + code locs │
    └────────────────────────────────────────┘
              ↓
    ┌────────────────────────────────────────┐
    │  B. ENGINEER AGENT (Fix Issues)        │
    │     - Take issue list                  │
    │     - Generate fixed template + CSS    │
    │     Output: Updated code               │
    └────────────────────────────────────────┘
          ↓
5. [MERGE & UPDATE] Collect outputs from parallel tracks
   - Extract updated resume template (if resume track ran)
   - Extract updated cover letter template (if cover letter track ran)
   - Update theme in database with new code
          ↓
6. [RENDER TEST PDFS] Generate new PDFs with fixed theme
   - Fetch first available resume from DB
   - Render resume and/or cover letter with updated theme
          ↓
7. [VERIFICATION AGENT] Check if fixes resolved problems
   - Compare new PDFs against original issue list
   - Determine if problems are resolved
          ↓
8. [RETRY LOGIC] If verification fails & retries remaining
   - Increment retry counter
   - Go back to step 4
   - Max 3 total attempts (configurable via request)
          ↓
9. [RESPONSE] Return summary with:
   - Original problems identified
   - Fixes applied
   - Verification status
   - URLs to new PDFs
```

---

## Detailed Implementation Steps

### Step 1: Create Pydantic Schemas

**File**: `/app/schemas/triage_schemas.py`

```python
"""Schemas for theme triage workflow"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Literal


class IssueIdentification(BaseModel):
    """Output schema for triage agent identifying issues"""
    issue_description: str = Field(
        description="Clear description of the visual/layout problem observed in the PDF"
    )
    severity: Literal["critical", "major", "minor"] = Field(
        description="Severity level of the issue"
    )
    code_location: str = Field(
        description="Where in the theme code this issue likely originates (e.g., 'header section of template', 'CSS .summary-text class')"
    )
    suggested_fix: str = Field(
        description="High-level suggestion for how to fix this issue"
    )


class TriageAnalysisOutput(BaseModel):
    """Complete output from a triage agent analyzing a PDF"""
    issues: List[IssueIdentification] = Field(
        description="List of all issues identified in the PDF"
    )
    overall_assessment: str = Field(
        description="2-3 sentence summary of the overall quality and main problems"
    )


class ThemeCodeUpdate(BaseModel):
    """Output schema for engineer agent fixing theme code"""
    template: str = Field(
        description="Complete fixed Jinja2 template code"
    )
    styles: str = Field(
        description="Complete fixed CSS code"
    )
    fixes_applied: List[str] = Field(
        description="List of specific fixes applied to address identified issues"
    )


class VerificationResult(BaseModel):
    """Output schema for verification agent"""
    all_issues_resolved: bool = Field(
        description="True if all original issues appear to be fixed in the new PDF"
    )
    remaining_issues: List[str] = Field(
        description="List of issues that are still present (empty if all resolved)"
    )
    new_issues: List[str] = Field(
        description="List of any new issues introduced by the fixes"
    )
    recommendation: str = Field(
        description="Recommendation: 'approve' if good, 'retry' if fixable, 'manual_review' if complex"
    )


class ThemeTriageRequest(BaseModel):
    """Request schema for theme triage endpoint"""
    theme_id: str
    max_retries: Optional[int] = Field(default=1, ge=0, le=3)
    
    @validator('max_retries')
    def validate_retries(cls, v):
        if v > 3:
            raise ValueError("max_retries cannot exceed 3")
        return v


class ThemeTriageResponse(BaseModel):
    """Response schema for theme triage endpoint"""
    status: int
    message: str
    data: dict
```

### Step 2: Create Triage Agent Definitions

**File**: `/app/agents/triage/triage_agents.py`

```python
"""
Triage Agents for Theme Quality Analysis and Repair

This module contains specialized agents for:
1. Analyzing PDFs to identify visual/layout problems
2. Mapping problems to theme code locations
3. Generating fixes for identified issues
4. Verifying that fixes resolved the problems
"""

from google.adk.agents import LlmAgent
from google.genai import types
from google.adk.planners import BuiltInPlanner
from app.schemas.triage_schemas import (
    TriageAnalysisOutput,
    ThemeCodeUpdate,
    VerificationResult
)
import json


def create_resume_triage_agent():
    """
    Creates an LlmAgent that analyzes a resume PDF to identify layout/design issues
    and maps them to problematic areas in the theme code.
    """
    return LlmAgent(
        model="gemini-2.5-flash",
        name="resume_triage_agent",
        description="Analyzes resume PDF to identify visual and structural problems",
        instruction=(
            "## Persona ##\n"
            "You are an expert document quality analyst with a keen eye for design flaws, "
            "layout problems, and typographic issues in professional resumes. You have deep "
            "knowledge of HTML/CSS rendering and common PDF generation problems.\n\n"
            
            "## Goal ##\n"
            "Your goal is to carefully analyze the provided resume PDF and identify ALL "
            "issues that make it look unprofessional, poorly formatted, or difficult to read. "
            "For each issue, you must map it to the likely location in the theme code.\n\n"
            
            "## Input ##\n"
            "You will receive:\n"
            "1. A resume PDF (as an image or text extraction)\n"
            "2. The theme's resume template (Jinja2 HTML)\n"
            "3. The theme's resume styles (CSS)\n\n"
            
            "## Common Issues to Look For ##\n"
            "- **Headers & Text Breaks**: Names or section headers split across pages/lines awkwardly\n"
            "- **Spacing Problems**: Excessive whitespace, sections too cramped, inconsistent margins\n"
            "- **Overflow**: Text running off page edges or overlapping\n"
            "- **Alignment**: Inconsistent alignment of bullets, dates, or text blocks\n"
            "- **Font Issues**: Font sizes too large/small, poor hierarchy, illegible text\n"
            "- **Section Breaks**: Awkward page breaks splitting related content\n"
            "- **Skills Section**: Skills breaking into multiple columns/rows incorrectly\n"
            "- **List Formatting**: Bullets not aligning, list items wrapped poorly\n"
            "- **Visual Hierarchy**: Important information not standing out, poor visual flow\n\n"
            
            "## Analysis Process ##\n"
            "1. Examine the PDF visually (or analyze the text/layout description)\n"
            "2. Identify each specific problem\n"
            "3. Classify severity: 'critical' (makes document unusable), 'major' (significantly hurts professionalism), 'minor' (small polish issue)\n"
            "4. Map each issue to the likely code location:\n"
            "   - Which Jinja2 template section contains the problematic element?\n"
            "   - Which CSS class or selector is causing the styling issue?\n"
            "5. Suggest a high-level fix for each issue\n\n"
            
            "## Output ##\n"
            "You must return a JSON object matching the TriageAnalysisOutput schema.\n"
            "Be thorough but precise - focus on real issues, not nitpicking.\n\n"
            
            f"## Required JSON Schema ##\n```json\n{TriageAnalysisOutput.model_json_schema()}\n```"
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.3,  # Low temperature for consistent analysis
            response_mime_type="application/json"
        ),
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_budget=2048  # More thinking budget for careful analysis
            )
        ),
        output_schema=TriageAnalysisOutput,
        output_key="resume_triage_analysis"
    )


def create_cover_letter_triage_agent():
    """
    Creates an LlmAgent that analyzes a cover letter PDF to identify layout/design issues.
    """
    return LlmAgent(
        model="gemini-2.5-flash",
        name="cover_letter_triage_agent",
        description="Analyzes cover letter PDF to identify visual and structural problems",
        instruction=(
            "## Persona ##\n"
            "You are an expert document quality analyst specializing in professional "
            "correspondence design. You have a keen eye for layout problems, typography "
            "issues, and formatting flaws in cover letters.\n\n"
            
            "## Goal ##\n"
            "Your goal is to carefully analyze the provided cover letter PDF and identify "
            "ALL issues that make it look unprofessional or poorly formatted. For each issue, "
            "you must map it to the likely location in the theme code.\n\n"
            
            "## Input ##\n"
            "You will receive:\n"
            "1. A cover letter PDF (as an image or text extraction)\n"
            "2. The theme's cover letter template (Jinja2 HTML)\n"
            "3. The theme's cover letter styles (CSS)\n\n"
            
            "## Common Issues to Look For ##\n"
            "- **Header Problems**: Sender/recipient information poorly formatted or positioned\n"
            "- **Date Formatting**: Date placement or format looks unprofessional\n"
            "- **Spacing**: Poor spacing between paragraphs, margins too large/small\n"
            "- **Alignment**: Body text not properly aligned, signature misplaced\n"
            "- **Line Length**: Lines too long (hard to read) or too short (looks choppy)\n"
            "- **Font Issues**: Font sizes inconsistent, poor hierarchy\n"
            "- **Page Breaks**: Content awkwardly split across pages\n"
            "- **Signature Block**: Closing and signature not properly formatted\n"
            "- **Overall Balance**: Letter doesn't fill page well or looks cramped\n\n"
            
            "## Analysis Process ##\n"
            "1. Examine the PDF visually\n"
            "2. Identify each specific problem\n"
            "3. Classify severity: 'critical', 'major', or 'minor'\n"
            "4. Map to code location (template section or CSS selector)\n"
            "5. Suggest a fix\n\n"
            
            "## Output ##\n"
            "Return a JSON object matching the TriageAnalysisOutput schema.\n\n"
            
            f"## Required JSON Schema ##\n```json\n{TriageAnalysisOutput.model_json_schema()}\n```"
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.3,
            response_mime_type="application/json"
        ),
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_budget=2048
            )
        ),
        output_schema=TriageAnalysisOutput,
        output_key="cover_letter_triage_analysis"
    )


def create_resume_engineer_agent():
    """
    Creates an LlmAgent that takes issue analysis and generates fixed theme code.
    """
    return LlmAgent(
        model="gemini-2.5-pro",
        name="resume_engineer_agent",
        description="Generates fixed resume theme code to address identified issues",
        instruction=(
            "## Persona ##\n"
            "You are an expert front-end engineer specializing in Jinja2 templating and "
            "print-optimized CSS. You excel at diagnosing and fixing layout problems in "
            "PDF-rendered documents.\n\n"
            
            "## Goal ##\n"
            "Your goal is to take a list of identified issues with a resume theme and "
            "generate completely fixed template and CSS code that resolves ALL the problems.\n\n"
            
            "## Input ##\n"
            "You will receive:\n"
            "1. The original resume template (Jinja2)\n"
            "2. The original resume styles (CSS)\n"
            "3. A detailed list of issues from the triage agent\n"
            "4. The ResumeResponse schema that the template must use\n\n"
            
            "## Requirements ##\n"
            "1. **Fix Every Issue**: Address all problems identified by the triage agent\n"
            "2. **Preserve Structure**: Maintain the overall layout intent of the theme\n"
            "3. **Schema Compliance**: Use exact field names from ResumeResponse schema\n"
            "4. **Print Optimization**: Follow best practices for PDF rendering:\n"
            "   - Use `pt` for font-size, `in` or `cm` for margins/padding\n"
            "   - Use `page-break-inside: avoid` on `.experience-item` only\n"
            "   - Avoid excessive spacing that causes single-page content to overflow\n"
            "5. **Complete Code**: Return FULL template and styles, not snippets\n"
            "6. **Document Changes**: List all fixes applied\n\n"
            
            "## Common Fixes ##\n"
            "- Reduce font sizes for overflowing sections\n"
            "- Add/adjust margins for spacing issues\n"
            "- Fix CSS selectors for alignment problems\n"
            "- Adjust line-height for cramped text\n"
            "- Add/remove page-break rules\n"
            "- Fix flexbox/grid layouts for proper wrapping\n\n"
            
            "## Output ##\n"
            "Return a JSON object with:\n"
            "- `template`: Complete fixed Jinja2 template\n"
            "- `styles`: Complete fixed CSS\n"
            "- `fixes_applied`: List of changes made\n\n"
            
            f"## Required JSON Schema ##\n```json\n{ThemeCodeUpdate.model_json_schema()}\n```"
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.4,  # Slightly higher for creative problem-solving
            response_mime_type="application/json"
        ),
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_budget=3072  # High budget for complex code generation
            )
        ),
        output_schema=ThemeCodeUpdate,
        output_key="resume_code_update"
    )


def create_cover_letter_engineer_agent():
    """
    Creates an LlmAgent that generates fixed cover letter theme code.
    """
    return LlmAgent(
        model="gemini-2.5-pro",
        name="cover_letter_engineer_agent",
        description="Generates fixed cover letter theme code to address identified issues",
        instruction=(
            "## Persona ##\n"
            "You are an expert front-end engineer specializing in Jinja2 templating and "
            "print-optimized CSS for professional correspondence.\n\n"
            
            "## Goal ##\n"
            "Generate completely fixed cover letter template and CSS that resolves all "
            "identified issues while maintaining professional appearance.\n\n"
            
            "## Input ##\n"
            "1. Original cover letter template (Jinja2)\n"
            "2. Original cover letter styles (CSS)\n"
            "3. Issue list from triage agent\n"
            "4. CoverLetterFull schema for field names\n\n"
            
            "## Requirements ##\n"
            "1. Fix all identified issues\n"
            "2. Maintain professional cover letter format\n"
            "3. Use exact field names from CoverLetterFull schema\n"
            "4. Follow print CSS best practices\n"
            "5. Return complete, working code\n\n"
            
            f"## Required JSON Schema ##\n```json\n{ThemeCodeUpdate.model_json_schema()}\n```"
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.4,
            response_mime_type="application/json"
        ),
        planner=BuiltInPlanner(
            thinking_config=types.ThinkingConfig(
                include_thoughts=True,
                thinking_budget=3072
            )
        ),
        output_schema=ThemeCodeUpdate,
        output_key="cover_letter_code_update"
    )


def create_verification_agent():
    """
    Creates an LlmAgent that verifies if fixes resolved the original problems.
    """
    return LlmAgent(
        model="gemini-2.5-flash",
        name="verification_agent",
        description="Verifies if theme fixes resolved identified issues",
        instruction=(
            "## Persona ##\n"
            "You are a quality assurance specialist who verifies that design fixes "
            "actually solved the problems they were meant to address.\n\n"
            
            "## Goal ##\n"
            "Compare the newly generated PDF(s) against the original issue list to "
            "determine if all problems have been resolved.\n\n"
            
            "## Input ##\n"
            "1. Original issue list(s) from triage agent(s)\n"
            "2. List of fixes that were applied\n"
            "3. New PDF(s) generated with fixed theme\n\n"
            
            "## Verification Process ##\n"
            "1. Check each original issue against the new PDF\n"
            "2. Determine if the issue is resolved, improved, or still present\n"
            "3. Identify any NEW issues introduced by the fixes\n"
            "4. Make a recommendation:\n"
            "   - 'approve': All issues resolved, quality is good\n"
            "   - 'retry': Some issues remain but are likely fixable with another pass\n"
            "   - 'manual_review': Complex issues require human intervention\n\n"
            
            "## Output ##\n"
            "Return detailed verification results in JSON format.\n\n"
            
            f"## Required JSON Schema ##\n```json\n{VerificationResult.model_json_schema()}\n```"
        ),
        generate_content_config=types.GenerateContentConfig(
            temperature=0.2,  # Very low temperature for objective assessment
            response_mime_type="application/json"
        ),
        output_schema=VerificationResult,
        output_key="verification_result"
    )
```

### Step 3: Create the Workflow Orchestrator

**File**: `/app/workflows/theme_triage_workflow.py`

```python
"""
Theme Triage Workflow Orchestrator

Coordinates the multi-agent workflow for analyzing and fixing theme issues.
"""

try:
    import os
    if os.getenv('USE_MOCK_ADK', 'false').lower() == 'true':
        raise ImportError("Mock ADK forced for testing")
    from google.adk.agents import ParallelAgent, SequentialAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    print("✅ Using real Google ADK")
except ImportError:
    print("⚠️ Google ADK not available, using mock implementation")
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from mock_adk import ParallelAgent, SequentialAgent, Runner, InMemorySessionService
    import types as mock_types
    types = mock_types

import uuid
import json
from typing import Dict, Any, Optional, List
from fastapi import UploadFile

from app.agents.triage.triage_agents import (
    create_resume_triage_agent,
    create_cover_letter_triage_agent,
    create_resume_engineer_agent,
    create_cover_letter_engineer_agent,
    create_verification_agent
)
from app.crud import crud_theme
from app.services.designer_pdf import create_designed_pdfs
from app.services.theme_service import save_theme_from_agents
from app.schemas.theme import ThemeSchema, ThemeTemplate
from app.schemas.theme_documents import ThemeDoc
from app.schemas.ResumeSchemas import ResumeResponse
from app.schemas.CoverLetterSchemas import CoverLetterFull


async def execute_theme_triage_workflow(
    theme_id: str,
    resume_pdf: Optional[UploadFile] = None,
    cover_letter_pdf: Optional[UploadFile] = None,
    max_retries: int = 1
) -> Dict[str, Any]:
    """
    Main orchestrator for theme triage workflow.
    
    Args:
        theme_id: ID of the theme package to analyze and fix
        resume_pdf: Optional uploaded resume PDF with issues
        cover_letter_pdf: Optional uploaded cover letter PDF with issues
        max_retries: Maximum number of retry attempts (0-3)
    
    Returns:
        Dictionary with workflow results including fixes and new PDFs
    """
    
    # Step 1: Validate inputs
    if not resume_pdf and not cover_letter_pdf:
        raise ValueError("At least one PDF (resume or cover letter) must be provided")
    
    # Step 2: Fetch theme package from database
    theme_package = await crud_theme.get_theme_package_by_id(theme_id)
    if not theme_package:
        raise ValueError(f"Theme package with ID {theme_id} not found")
    
    # Fetch the actual theme components
    resume_theme_doc = await crud_theme.get_theme_by_id(theme_package.resumeTemplateId)
    cover_letter_theme_doc = await crud_theme.get_theme_by_id(theme_package.coverLetterTemplateId)
    
    if not resume_theme_doc or not cover_letter_theme_doc:
        raise ValueError("Theme components not found")
    
    # Step 3: Build the dynamic multi-agent workflow based on what PDFs were provided
    attempt = 0
    verification_passed = False
    workflow_results = {}
    
    while attempt <= max_retries and not verification_passed:
        attempt += 1
        print(f"\n{'='*60}")
        print(f"🔄 THEME TRIAGE ATTEMPT {attempt}/{max_retries + 1}")
        print(f"{'='*60}\n")
        
        # Step 4: Construct sequential workflows for each uploaded PDF
        sub_agents = []
        
        # Resume workflow (if resume PDF provided)
        if resume_pdf:
            resume_triage = create_resume_triage_agent()
            resume_engineer = create_resume_engineer_agent()
            
            resume_workflow = SequentialAgent(
                name="resume_triage_workflow",
                description="Analyzes resume PDF issues and generates fixes",
                sub_agents=[resume_triage, resume_engineer]
            )
            sub_agents.append(resume_workflow)
        
        # Cover letter workflow (if cover letter PDF provided)
        if cover_letter_pdf:
            cover_triage = create_cover_letter_triage_agent()
            cover_engineer = create_cover_letter_engineer_agent()
            
            cover_workflow = SequentialAgent(
                name="cover_letter_triage_workflow",
                description="Analyzes cover letter PDF issues and generates fixes",
                sub_agents=[cover_triage, cover_engineer]
            )
            sub_agents.append(cover_workflow)
        
        # Step 5: Run workflows in parallel
        parallel_triage_workflow = ParallelAgent(
            name="parallel_triage_workflow",
            description="Runs resume and/or cover letter triage in parallel",
            sub_agents=sub_agents
        )
        
        # Step 6: Execute the workflow
        session_service = InMemorySessionService()
        session_id = f"theme_triage_{theme_id}_{uuid.uuid4().hex[:8]}"
        await session_service.create_session(
            session_id=session_id,
            app_name="theme_triage",
            user_id="system"
        )
        
        runner = Runner(
            agent=parallel_triage_workflow,
            session_service=session_service,
            app_name="theme_triage"
        )
        
        # Construct input with PDF data and theme code
        content_parts = []
        
        # Add text context
        context_text = f"Theme ID: {theme_id}\nTheme Name: {theme_package.name}\n\n"
        
        if resume_pdf:
            # Read PDF as bytes (in real implementation, extract text or convert to image)
            resume_bytes = await resume_pdf.read()
            context_text += f"=== RESUME THEME CODE ===\n\n"
            context_text += f"Template:\n{resume_theme_doc.template}\n\n"
            context_text += f"Styles:\n{resume_theme_doc.styles}\n\n"
            # Note: In production, you'd want to extract text from PDF or convert to image
            # For now, we'll pass the PDF info in the text prompt
            context_text += f"Resume PDF provided: {resume_pdf.filename} ({len(resume_bytes)} bytes)\n\n"
        
        if cover_letter_pdf:
            cover_bytes = await cover_letter_pdf.read()
            context_text += f"=== COVER LETTER THEME CODE ===\n\n"
            context_text += f"Template:\n{cover_letter_theme_doc.template}\n\n"
            context_text += f"Styles:\n{cover_letter_theme_doc.styles}\n\n"
            context_text += f"Cover letter PDF provided: {cover_letter_pdf.filename} ({len(cover_bytes)} bytes)\n\n"
        
        content_parts.append(types.Part(text=context_text))
        
        content = types.Content(role='user', parts=content_parts)
        
        # Run the workflow
        final_response = {}
        async for event in runner.run_async(
            new_message=content,
            session_id=session_id,
            user_id="system"
        ):
            if event.is_final_response() and hasattr(event, 'content') and event.content:
                response_text = event.content.parts[0].text
                try:
                    response_data = json.loads(response_text)
                    
                    # Map agent outputs
                    if event.author == "resume_triage_agent":
                        final_response["resume_triage_analysis"] = response_data
                    elif event.author == "resume_engineer_agent":
                        final_response["resume_code_update"] = response_data
                    elif event.author == "cover_letter_triage_agent":
                        final_response["cover_letter_triage_analysis"] = response_data
                    elif event.author == "cover_letter_engineer_agent":
                        final_response["cover_letter_code_update"] = response_data
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse JSON from {event.author}: {e}")
        
        # Step 7: Update theme in database with fixes
        updated_theme_ids = {}
        
        if "resume_code_update" in final_response:
            resume_update = final_response["resume_code_update"]
            resume_theme_doc.template = resume_update["template"]
            resume_theme_doc.styles = resume_update["styles"]
            await resume_theme_doc.save()
            updated_theme_ids["resume"] = str(resume_theme_doc.id)
            print(f"✅ Updated resume theme: {updated_theme_ids['resume']}")
        
        if "cover_letter_code_update" in final_response:
            cover_update = final_response["cover_letter_code_update"]
            cover_letter_theme_doc.template = cover_update["template"]
            cover_letter_theme_doc.styles = cover_update["styles"]
            await cover_letter_theme_doc.save()
            updated_theme_ids["cover_letter"] = str(cover_letter_theme_doc.id)
            print(f"✅ Updated cover letter theme: {updated_theme_ids['cover_letter']}")
        
        # Step 8: Render new PDFs with fixed theme
        # Fetch a test resume and cover letter from database
        test_resume = await ResumeResponse.find_one({})
        test_cover_letter = await CoverLetterFull.find_one({})
        
        if not test_resume:
            raise ValueError("No resume found in database for test rendering")
        if not test_cover_letter:
            raise ValueError("No cover letter found in database for test rendering")
        
        # Build ThemeSchema from updated theme docs
        theme_schema = ThemeSchema(
            name=theme_package.name,
            description=theme_package.description,
            resume_template=ThemeTemplate(
                template=resume_theme_doc.template,
                styles=resume_theme_doc.styles
            ),
            cover_letter_template=ThemeTemplate(
                template=cover_letter_theme_doc.template,
                styles=cover_letter_theme_doc.styles
            )
        )
        
        # Render PDFs
        pdf_result = create_designed_pdfs(
            resume_obj=test_resume.model_dump(),
            cover_letter_obj=test_cover_letter.model_dump(),
            theme=theme_schema,
            upload=True  # Upload to Cloudinary for verification
        )
        
        print(f"✅ Generated new PDFs: {pdf_result}")
        
        # Step 9: Run verification agent
        verification_agent = create_verification_agent()
        verification_session_id = f"verification_{uuid.uuid4().hex[:8]}"
        await session_service.create_session(
            session_id=verification_session_id,
            app_name="theme_triage_verification",
            user_id="system"
        )
        
        verification_runner = Runner(
            agent=verification_agent,
            session_service=session_service,
            app_name="theme_triage_verification"
        )
        
        verification_input = {
            "original_issues": final_response,
            "new_pdfs": pdf_result,
            "fixes_applied": {
                "resume": final_response.get("resume_code_update", {}).get("fixes_applied", []),
                "cover_letter": final_response.get("cover_letter_code_update", {}).get("fixes_applied", [])
            }
        }
        
        verification_content = types.Content(
            role='user',
            parts=[types.Part(text=json.dumps(verification_input, indent=2))]
        )
        
        verification_result = None
        async for event in verification_runner.run_async(
            new_message=verification_content,
            session_id=verification_session_id,
            user_id="system"
        ):
            if event.is_final_response() and hasattr(event, 'content'):
                try:
                    verification_result = json.loads(event.content.parts[0].text)
                except json.JSONDecodeError:
                    pass
        
        # Step 10: Check verification result
        if verification_result and verification_result.get("all_issues_resolved"):
            verification_passed = True
            print(f"✅ Verification PASSED on attempt {attempt}")
        else:
            print(f"⚠️ Verification FAILED on attempt {attempt}")
            if attempt < max_retries + 1:
                print(f"🔄 Retrying... ({max_retries + 1 - attempt} attempts remaining)")
        
        # Store workflow results for final response
        workflow_results = {
            "attempt": attempt,
            "original_issues": final_response,
            "updates_applied": updated_theme_ids,
            "new_pdfs": pdf_result,
            "verification": verification_result
        }
    
    # Step 11: Build final response
    return {
        "success": verification_passed,
        "attempts": attempt,
        "max_retries": max_retries,
        "theme_id": theme_id,
        "theme_name": theme_package.name,
        "results": workflow_results
    }
```

### Step 4: Create the API Endpoint

**File**: `/app/api/v1/endpoints/themes.py` (add to existing router)

Add these imports at the top:
```python
from fastapi import Form
from app.workflows.theme_triage_workflow import execute_theme_triage_workflow
from app.schemas.triage_schemas import ThemeTriageResponse
```

Add this endpoint:

```python
@router.post("/triage/{theme_id}", response_model=ThemeTriageResponse)
async def triage_theme(
    theme_id: str,
    resume_pdf: Optional[UploadFile] = File(None),
    cover_letter_pdf: Optional[UploadFile] = File(None),
    max_retries: int = Form(default=1, ge=0, le=3)
):
    """
    Intelligent theme triage and repair workflow.
    
    Uploads a resume and/or cover letter PDF with visual/layout issues, and the system:
    1. Analyzes the PDF(s) to identify problems
    2. Maps issues to theme code locations
    3. Generates fixes for all identified issues
    4. Updates the theme in the database
    5. Renders new PDFs to verify fixes
    6. Optionally retries if issues remain
    
    Args:
        theme_id: ID of the theme package to analyze and fix
        resume_pdf: Optional resume PDF with issues (at least one PDF required)
        cover_letter_pdf: Optional cover letter PDF with issues (at least one PDF required)
        max_retries: Number of retry attempts if verification fails (0-3, default 1)
    
    Returns:
        Summary of issues found, fixes applied, and verification results
    
    Example usage:
        curl -X POST "http://localhost:8000/api/v1/themes/triage/THEME_ID" \
          -F "resume_pdf=@problem_resume.pdf" \
          -F "max_retries=2"
    """
    
    try:
        # Validate that at least one PDF is provided
        if not resume_pdf and not cover_letter_pdf:
            raise HTTPException(
                status_code=400,
                detail="At least one PDF (resume_pdf or cover_letter_pdf) must be provided"
            )
        
        # Execute the workflow
        result = await execute_theme_triage_workflow(
            theme_id=theme_id,
            resume_pdf=resume_pdf,
            cover_letter_pdf=cover_letter_pdf,
            max_retries=max_retries
        )
        
        # Build response
        return {
            "status": 200 if result["success"] else 206,  # 206 = Partial Content (fixes attempted but not verified)
            "message": (
                f"Theme triage completed successfully in {result['attempts']} attempt(s)"
                if result["success"]
                else f"Theme triage completed with issues remaining after {result['attempts']} attempt(s)"
            ),
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Theme triage failed: {str(e)}")
```

---

## Testing Strategy

### Unit Tests
1. Test each agent individually with mock inputs
2. Test schema validation for all Pydantic models
3. Test PDF extraction/conversion utilities

### Integration Tests
1. Test workflow with single resume PDF
2. Test workflow with single cover letter PDF
3. Test workflow with both PDFs
4. Test retry logic
5. Test database updates

### End-to-End Tests
1. Upload real problematic PDFs and verify fixes
2. Test with various types of issues (spacing, alignment, overflow)
3. Verify that fixed PDFs actually look better

---

## Implementation Notes

### Google ADK Agent Composition Patterns

Based on the existing codebase patterns (especially `/app/features/theme_generator.py` and `/app/features/cover_letter_orchestrator.py`):

1. **Sequential Agents**: Used when agents must run in order, with each agent's output feeding into the next
   ```python
   SequentialAgent(
       name="workflow_name",
       sub_agents=[agent1, agent2, agent3]
   )
   ```

2. **Parallel Agents**: Used when agents can run independently and simultaneously
   ```python
   ParallelAgent(
       name="parallel_name",
       sub_agents=[agent1, agent2]
   )
   ```

3. **Nested Composition**: You can nest Sequential inside Parallel and vice versa
   ```python
   ParallelAgent(
       sub_agents=[
           SequentialAgent(sub_agents=[triage, engineer]),  # Resume track
           SequentialAgent(sub_agents=[triage, engineer])   # Cover letter track
       ]
   )
   ```

4. **Output Keys**: Each agent's `output_key` is used to retrieve its results from the workflow
   ```python
   LlmAgent(
       output_key="my_agent_output",
       output_schema=MySchema
   )
   ```

5. **Session Management**: Always create sessions before running workflows
   ```python
   session_service = InMemorySessionService()
   session_id = uuid.uuid4().hex
   await session_service.create_session(session_id=session_id, app_name="app_name", user_id="user")
   ```

### PDF Handling Considerations

1. **PDF to Text/Image**: The agents need to analyze PDF content. Options:
   - Extract text using PyPDF2 or pdfplumber
   - Convert PDF to images using pdf2image
   - Use Gemini's multimodal capabilities to analyze PDF images directly

2. **PDF Upload**: Use FastAPI's `UploadFile` with `File()` parameter
   ```python
   resume_pdf: UploadFile = File(None)
   ```

3. **Multipart Form Data**: Since we're uploading files, the endpoint uses `multipart/form-data`:
   - File params use `File()`
   - Other params use `Form()`

### Database Update Pattern

Following the pattern in `/app/services/theme_service.py`:

1. Fetch theme documents using Beanie
2. Update the template and styles fields
3. Call `.save()` to persist changes
4. No need to manually create new documents - update in place

### Error Handling

1. Validate inputs before starting workflow
2. Use try/except blocks around agent execution
3. Return partial results if workflow fails mid-execution
4. Log all errors for debugging

---

## Dependencies

### Required Packages (Already in Project)
- `google-adk` - Agent Development Kit
- `google-genai` - Gemini API
- `weasyprint` - PDF rendering
- `jinja2` - Template rendering
- `beanie` - MongoDB ODM
- `fastapi` - Web framework

### Optional Enhancements
- `pdf2image` - Convert PDFs to images for visual analysis
- `pdfplumber` - Extract text and layout info from PDFs
- `pillow` - Image processing

---

## Success Metrics

1. **Accuracy**: % of issues correctly identified by triage agents
2. **Fix Rate**: % of identified issues successfully fixed by engineer agents
3. **Verification Rate**: % of workflows that pass verification on first attempt
4. **User Satisfaction**: Manual review of fixed themes shows improvement

---

## Future Enhancements

1. **Learning Loop**: Store successful fixes to train future agents
2. **Issue Taxonomy**: Build categorization of common theme problems
3. **Automated Testing**: Generate test PDFs for new themes automatically
4. **Visual Diff**: Show side-by-side comparison of before/after PDFs
5. **Batch Processing**: Triage multiple themes at once
6. **A/B Testing**: Generate multiple fix variations and choose best

---

## Related Documentation

- [Theme Creation Workflow](./THEME_CREATION_WORKFLOW.md)
- [Designer Agent Documentation](../agents/designer/Designer_Agent.md)
- [Multipart Form Data Fix](./STRATEGIC_API_MULTIPART_FIX.md)
- [Schema Assembler Plan](./SCHEMA_ASSEMBLER_PLAN.md)

---

## Acceptance Checklist

- [ ] All Pydantic schemas created and validated
- [ ] All agent definitions implemented with correct output schemas
- [ ] Workflow orchestrator handles conditional routing correctly
- [ ] Parallel agent runs both tracks when both PDFs provided
- [ ] Sequential agents run triage → engineer in correct order
- [ ] Database updates persist correctly
- [ ] PDF rendering works with updated themes
- [ ] Verification agent provides accurate assessment
- [ ] Retry logic works up to max_retries limit
- [ ] API endpoint returns correct response format
- [ ] Error handling covers all edge cases
- [ ] Documentation updated with examples
- [ ] Integration tests pass
- [ ] Manual testing confirms fixes work

---

## Story Points
**Estimate**: 13 points (Large - Complex multi-agent workflow)

## Sprint Assignment
Recommended for 2-sprint implementation:
- **Sprint 1**: Schemas, agents, basic workflow (no retry logic)
- **Sprint 2**: Full workflow, retry logic, endpoint, testing
