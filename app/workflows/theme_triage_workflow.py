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
    print("✅ Using real Google ADK for triage workflow")
except ImportError:
    print("⚠️ Google ADK not available, using mock implementation for triage workflow")
    from app.mocks.mock_adk import (
        ParallelAgent, SequentialAgent, LlmAgent, Runner,
        InMemorySessionService, FunctionTool, google_search, agent_tool
    )
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
            # Reset file position for potential re-reads
            await resume_pdf.seek(0)
        
        if cover_letter_pdf:
            cover_bytes = await cover_letter_pdf.read()
            context_text += f"=== COVER LETTER THEME CODE ===\n\n"
            context_text += f"Template:\n{cover_letter_theme_doc.template}\n\n"
            context_text += f"Styles:\n{cover_letter_theme_doc.styles}\n\n"
            context_text += f"Cover letter PDF provided: {cover_letter_pdf.filename} ({len(cover_bytes)} bytes)\n\n"
            # Reset file position
            await cover_letter_pdf.seek(0)
        
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
