"""
Cover Letter Orchestrator

Coordinates the multi-agent workflow for generating strategic cover letters.
"""

try:
    import os
    # Try to use real Google ADK by default, fall back to mock for testing
    if os.getenv('USE_MOCK_ADK', 'false').lower() == 'true':
        raise ImportError("Mock ADK forced for testing")
    from google.adk.agents import SequentialAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    print("✅ Using real Google ADK")
except ImportError:
    print("⚠️ Google ADK not available, using mock implementation")
    # Import mock implementation
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    from mock_adk import SequentialAgent, Runner, InMemorySessionService
    # Mock types module
    import types
    types.GenerateContentConfig = type('GenerateContentConfig', (), {
        '__init__': lambda self, temperature=0.1, response_mime_type="application/json": None
    })
    types.Content = type('Content', (), {
        '__init__': lambda self, role, parts: None
    })
    types.Part = type('Part', (), {
        '__init__': lambda self, text=None, inline_data=None: None
    })

import chromadb
import asyncio
import uuid
import json
from typing import Dict, Any, Optional, List
from datetime import datetime

from app.services.resume_service import get_resume_pydantic
from app.tools.get_url_contents import get_url_contents
from app.agents.cover_letter.analyst_agent import create_cover_letter_analyst_agent, run_cover_letter_analysis
from app.agents.cover_letter.writer_agent import create_cover_letter_writer_agent, run_cover_letter_writing
from app.agents.cover_letter.editor_agent import create_cover_letter_editor_agent, run_cover_letter_editing
from app.db.session import SessionLocal
from app.services.cover_letter_service import save_cover_letter


def process_resume_for_chroma(resume_json: dict) -> tuple[list[str], list[dict], list[str]]:
    """
    Convert a resume JSON object into documents, metadatas and ids for ChromaDB.
    Same logic as strategic resume analysis for consistency.
    """

    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    # Process Experience
    for job in resume_json.get("experience", []):
        responsibilities = job.get("responsibilities", [])
        if isinstance(responsibilities, str):
            responsibilities = [r.strip() for r in responsibilities.splitlines() if r.strip()]

        for responsibility in responsibilities:
            if not responsibility:
                continue
            documents.append(responsibility)
            metadatas.append({
                "type": "experience",
                "company": job.get("company") or "Unknown Company",
                "position": job.get("position") or "Unknown Position",
                "startDate": job.get("startDate") or "Unknown",
                "endDate": job.get("endDate") or "Unknown"
            })
            ids.append(str(uuid.uuid4()))

    # Process Projects
    for project in resume_json.get("projects", []):
        name = project.get("name", "") or ""
        desc = project.get("description", "") or ""
        doc_content = f"{name}: {desc}".strip(": ").strip()
        if not doc_content:
            continue
        documents.append(doc_content)
        metadatas.append({
            "type": "project",
            "name": project.get("name") or "Unknown Project",
        })
        ids.append(project.get("id") or str(uuid.uuid4()))

    # Process Skills
    skill_list = [skill.get("name") for skill in resume_json.get("skills", []) if skill.get("name")]
    if skill_list:
        skill_summary = "Key technical skills include: " + ", ".join(skill_list)
        documents.append(skill_summary)
        metadatas.append({"type": "skills_summary"})
        ids.append("skills_summary_01")

    # Process Summary
    if resume_json.get("summary"):
        documents.append(resume_json["summary"])
        metadatas.append({"type": "summary"})
        ids.append("main_summary_01")

    # Process Education
    for education in resume_json.get("education", []):
        institution = education.get("institution", "") or ""
        degree = education.get("degree", "") or ""
        doc_content = f"{degree} from {institution}".strip()
        if not doc_content or doc_content == "from":
            continue
        documents.append(doc_content)
        metadatas.append({
            "type": "education",
            "institution": institution,
            "degree": degree,
            "startDate": education.get("startDate") or "Unknown",
            "endDate": education.get("endDate") or "Unknown"
        })
        ids.append(education.get("id") or str(uuid.uuid4()))

    return documents, metadatas, ids


async def cover_letter_orchestrator(
    resume_id: str,
    job_description_url: str,
    optional_prompt: Optional[str] = None,
    save_to_db: bool = True
) -> Dict[str, Any]:
    """
    Main orchestrator for the strategic cover letter generation workflow.

    Args:
        resume_id: ID of the resume to use
        job_description_url: URL of the job description to analyze
        optional_prompt: Optional user prompt for tone or focus

    Returns:
        Dict containing the generated cover letter data
    """

    print("🚀 Starting strategic cover letter generation...")

    # Step 1: Validate inputs and fetch resume
    print("📄 Step 1: Fetching resume data...")
    resume = get_resume_pydantic(resume_id)
    if not resume:
        raise ValueError(f"Resume not found for id: {resume_id}")

    # Step 2: Initialize ChromaDB and store resume data
    print("🗄️ Step 2: Setting up ChromaDB for resume analysis...")
    chroma_client = chromadb.EphemeralClient()
    resume_collection = chroma_client.get_or_create_collection(name="cover_letter_resume")

    documents, metadatas, ids = process_resume_for_chroma(resume.model_dump())
    if not documents:
        raise ValueError("No resume data found to process")
    resume_collection.add(documents=documents, metadatas=metadatas, ids=ids)

    # Step 3: Fetch and store job description
    print("🌐 Step 3: Fetching job description...")
    job_description_chunks = await get_url_contents(job_description_url)
    jd_collection = chroma_client.get_or_create_collection(name=f"cover_letter_jd_{str(uuid.uuid4())[:8]}")
    jd_collection.add(
        documents=job_description_chunks,
        metadatas=[{"source": job_description_url}] * len(job_description_chunks),
        ids=[str(uuid.uuid4()) for _ in job_description_chunks],
    )

    # Step 4: Set up query tools
    def resume_query_tool(queries: list[str], top_k: int = 4) -> list[dict]:
        """Query resume collection for relevant information."""
        resume_parts = []
        results = resume_collection.query(query_texts=queries, n_results=top_k)
        for doc, meta, score in zip(results.get('documents', []), results.get('metadatas', []), results.get('distances', [])):
            resume_parts.append({"document": doc, "metadata": meta, "score": score})
        return resume_parts

    def job_description_query_tool(queries: list[str], top_k: int = 10) -> list[dict]:
        """Query job description collection for relevant information."""
        jd_parts = []
        results = jd_collection.query(query_texts=queries, n_results=top_k)
        for doc, meta, score in zip(results.get('documents', []), results.get('metadatas', []), results.get('distances', [])):
            jd_parts.append({"document": doc, "metadata": meta, "score": score})
        return jd_parts

    # Step 5: Create agents
    print("🤖 Step 4: Creating analysis agents...")
    analyst_agent = create_cover_letter_analyst_agent(resume_query_tool, job_description_query_tool)
    writer_agent = create_cover_letter_writer_agent(resume_query_tool, job_description_query_tool)
    editor_agent = create_cover_letter_editor_agent()

    # Step 6: Set up session service
    session_service = InMemorySessionService()
    base_session_id = str(uuid.uuid4())[:8]

    # Step 7: Run analysis phase
    print("🔍 Step 5: Running cover letter analysis...")
    analysis_session_id = f"analysis_{base_session_id}"
    analysis_result = await run_cover_letter_analysis(
        analyst_agent, resume_id, job_description_url,
        session_service, analysis_session_id
    )

    if not analysis_result:
        raise ValueError("Failed to generate cover letter analysis")

    # Step 8: Run writing phase
    print("✍️ Step 6: Writing cover letter content...")
    writing_session_id = f"writing_{base_session_id}"
    writing_result = await run_cover_letter_writing(
        writer_agent, analysis_result, resume_id, job_description_url,
        optional_prompt, session_service, writing_session_id
    )

    if not writing_result:
        raise ValueError("Failed to generate cover letter content")

    # Step 9: Run editing phase
    print("✨ Step 7: Editing and polishing content...")
    editing_session_id = f"editing_{base_session_id}"
    editing_result = await run_cover_letter_editing(
        editor_agent, writing_result, analysis_result,
        session_service, editing_session_id
    )

    if not editing_result:
        raise ValueError("Failed to edit cover letter content")

    # Step 10: Assemble final response
    print("📋 Step 8: Assembling final cover letter...")
    final_content = assemble_cover_letter_content(editing_result)

    # Build response
    response_data = {
        "title": "Strategic Cover Letter",
        "jobDetails": {
            "title": analysis_result.get("role_summary", ""),
            "company": analysis_result.get("company_summary", ""),
            "url": job_description_url
        },
        "openingParagraph": editing_result.get("opening_paragraph", ""),
        "bodyParagraphs": editing_result.get("body_paragraphs", []),
        "companyConnection": editing_result.get("company_connection"),
        "closingParagraph": editing_result.get("closing_paragraph", ""),
        "tone": editing_result.get("tone", "professional"),
        "finalContent": final_content,
        "resumeId": resume_id,
        "createdAt": datetime.now().isoformat(),
        "updatedAt": datetime.now().isoformat(),
        "wordCount": editing_result.get("word_count", 0),
        "atsScore": editing_result.get("ats_score", 7)
    }

    # Persist to database if requested
    if save_to_db:
        print("💾 Step 9: Saving cover letter to database...")
        db = SessionLocal()
        try:
            saved_cover_letter = save_cover_letter(response_data, db)
            response_data['coverLetterId'] = saved_cover_letter['id']
            print(f"✅ Cover letter saved with ID: {saved_cover_letter['id']}")
        except Exception as e:
            print(f"⚠️ Failed to save cover letter to database: {e}")
            # Don't fail the entire request, just log the error
            response_data['persistenceError'] = str(e)
        finally:
            db.close()

    print("✅ Strategic cover letter generation completed!")
    return response_data


def assemble_cover_letter_content(edited_content: Dict[str, Any]) -> str:
    """
    Assemble the edited content into a final formatted cover letter string.

    Args:
        edited_content: The edited content from the editor agent

    Returns:
        Formatted cover letter as HTML/markdown string
    """

    paragraphs = []

    # Add opening paragraph
    if edited_content.get("opening_paragraph"):
        paragraphs.append(edited_content["opening_paragraph"])

    # Add body paragraphs
    for body_para in edited_content.get("body_paragraphs", []):
        if body_para.strip():
            paragraphs.append(body_para)

    # Add company connection if present
    if edited_content.get("company_connection"):
        paragraphs.append(edited_content["company_connection"])

    # Add closing paragraph
    if edited_content.get("closing_paragraph"):
        paragraphs.append(edited_content["closing_paragraph"])

    # Join paragraphs with double line breaks for readability
    return "\n\n".join(paragraphs)
