import os
import logging
import chromadb
import json
import asyncio
import uuid
from typing import List, Optional
from pydantic import BaseModel, Field

from app.tools.get_url_contents import get_url_contents
from app.schemas.ResumeSchemas import ResumeResponse
from app.agents.resume.strategic.strategic_resume_agent import process_resumes_for_chroma, gpt5_model, search_agent_tool

try:
    from google.adk.agents import ParallelAgent, SequentialAgent
    from google.adk.agents.llm_agent import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
except ImportError:
    # Fallback for mock environment if needed, similar to strategic_resume_agent
    from app.mocks.mock_adk import (
        ParallelAgent, SequentialAgent, LlmAgent, Runner,
        InMemorySessionService, types
    )

# --- Output Schemas ---

class ExperienceMarkdownOutput(BaseModel):
    experience_markdown: str = Field(description="The experience section formatted as Markdown.")

class SkillsMarkdownOutput(BaseModel):
    skills_markdown: str = Field(description="The skills section formatted as Markdown.")

class ProjectsMarkdownOutput(BaseModel):
    projects_markdown: str = Field(description="The projects section formatted as Markdown.")

class EducationMarkdownOutput(BaseModel):
    education_markdown: str = Field(description="The education section formatted as Markdown.")

class SummaryMarkdownOutput(BaseModel):
    summary_markdown: str = Field(description="The professional summary formatted as Markdown.")

# --- Agent Definition ---

async def markdown_resume_agent(
    resume: ResumeResponse,
    job_description_url: str
):
    # Initialize ChromaDB client
    chroma_client = chromadb.EphemeralClient()
    resume_collection = chroma_client.get_or_create_collection(name="resume_parts")

    if not resume:
        raise ValueError(f"Resume not found for id: {resume.id}")

    logging.info(f"Processing resume for id: {resume.id}")
    documents, metadatas, ids = process_resumes_for_chroma(resume.model_dump())
    if not documents:
        raise ValueError("No resume data found to process; cancelling the process.")
    resume_collection.add(documents=documents, metadatas=metadatas, ids=ids)

    # Fetch job description chunks
    job_description_chunks = await get_url_contents(job_description_url)
    jd_collection = chroma_client.get_or_create_collection(name=f"jd_{str(uuid.uuid4())[:8]}")
    jd_collection.add(
        documents=job_description_chunks,
        metadatas=[{"source": job_description_url}] * len(job_description_chunks),
        ids=[str(uuid.uuid4()) for _ in job_description_chunks],
    )

    def resume_query_tool(queries: list[str], top_k: int = 4) -> list[dict]:
        """Query resume collection for relevant information based on search terms."""
        resume_parts = []
        results = resume_collection.query(query_texts=queries, n_results=top_k)
        for doc, meta, score in zip(results.get('documents', []), results.get('metadatas', []), results.get('distances', [])):
            resume_parts.append({"document": doc, "metadata": meta, "score": score})
        return resume_parts

    def job_description_query_tool(queries: list[str], top_k: int = 10) -> list[dict]:
        """Query job description collection for relevant information based on search terms."""
        jd_parts = []
        results = jd_collection.query(query_texts=queries, n_results=top_k)
        for doc, meta, score in zip(results.get('documents', []), results.get('metadatas', []), results.get('distances', [])):
            jd_parts.append({"document": doc, "metadata": meta, "score": score})
        return jd_parts

    # --- Sub-Agents ---

    experience_agent = LlmAgent(
        model=gpt5_model,
        name="experience_markdown_agent",
        description="Generate the experience section as Markdown.",
        instruction=(
            "You are an expert Resume Writer. Your goal is to write the 'Experience' section of a resume, tailored to a specific job description.\n"
            "Use the tools to analyze the job description and the candidate's background.\n"
            "Select the most relevant experiences and write them in a clear, professional Markdown format.\n"
            "Use standard Markdown formatting (## for headers, ** for bold, * for bullets).\n"
            "Do NOT include the main 'Experience' header, just the content (job titles, companies, dates, bullets).\n"
            "Format each job clearly, e.g.:\n"
            "**Job Title** | Company Name\n"
            "*Dates*\n"
            "* Responsibility 1\n"
            "* Responsibility 2\n\n"
            "Output MUST be a JSON object with a single key 'experience_markdown'."
        ),
        output_schema=ExperienceMarkdownOutput,
        output_key="experience_markdown",
        tools=[resume_query_tool, job_description_query_tool]
    )

    skills_agent = LlmAgent(
        model=gpt5_model,
        name="skills_markdown_agent",
        description="Generate the skills section as Markdown.",
        instruction=(
            "You are an expert Resume Writer. Your goal is to write the 'Skills' section of a resume, tailored to a specific job description.\n"
            "Use the tools to analyze the job description and the candidate's background.\n"
            "Select the most relevant skills and group them logically (e.g., Languages, Frameworks, Tools).\n"
            "Use standard Markdown formatting.\n"
            "Do NOT include the main 'Skills' header.\n"
            "Output MUST be a JSON object with a single key 'skills_markdown'."
        ),
        output_schema=SkillsMarkdownOutput,
        output_key="skills_markdown",
        tools=[resume_query_tool, job_description_query_tool, search_agent_tool]
    )

    projects_agent = LlmAgent(
        model=gpt5_model,
        name="projects_markdown_agent",
        description="Generate the projects section as Markdown.",
        instruction=(
            "You are an expert Resume Writer. Your goal is to write the 'Projects' section of a resume, tailored to a specific job description.\n"
            "Use the tools to analyze the job description and the candidate's background.\n"
            "Select the most relevant projects.\n"
            "Use standard Markdown formatting.\n"
            "Do NOT include the main 'Projects' header.\n"
            "Format each project clearly, e.g.:\n"
            "**Project Name**\n"
            "* Description/Bullets\n\n"
            "Output MUST be a JSON object with a single key 'projects_markdown'."
        ),
        output_schema=ProjectsMarkdownOutput,
        output_key="projects_markdown",
        tools=[resume_query_tool, job_description_query_tool]
    )

    education_agent = LlmAgent(
        model=gpt5_model,
        name="education_markdown_agent",
        description="Generate the education section as Markdown.",
        instruction=(
            "You are an expert Resume Writer. Your goal is to write the 'Education' section of a resume.\n"
            "Use the tools to find the candidate's education history.\n"
            "Use standard Markdown formatting.\n"
            "Do NOT include the main 'Education' header.\n"
            "Format each entry clearly.\n"
            "Output MUST be a JSON object with a single key 'education_markdown'."
        ),
        output_schema=EducationMarkdownOutput,
        output_key="education_markdown",
        tools=[resume_query_tool]
    )

    summary_agent = LlmAgent(
        model=gpt5_model,
        name="summary_markdown_agent",
        description="Generate the professional summary as Markdown.",
        instruction=(
            "You are an expert Resume Writer. Your goal is to write a compelling professional summary, tailored to a specific job description.\n"
            "Use the tools to analyze the job description and the candidate's background.\n"
            "Write a 3-5 sentence summary.\n"
            "Use standard Markdown formatting (you can use bolding for emphasis).\n"
            "Do NOT include a 'Summary' header.\n"
            "Output MUST be a JSON object with a single key 'summary_markdown'."
        ),
        output_schema=SummaryMarkdownOutput,
        output_key="summary_markdown",
        tools=[resume_query_tool, job_description_query_tool]
    )

    # Run analysis agents in parallel
    resume_analysis_agent = ParallelAgent(
        name="resume_analysis_agent",
        description="Analyze resume and job description to extract relevant sections as Markdown.",
        sub_agents=[
            experience_agent,
            skills_agent,
            projects_agent,
            education_agent,
            summary_agent
        ]
    )

    # Create a session and run the agent
    session_service = InMemorySessionService()
    session_id = uuid.uuid4().hex
    session = await session_service.create_session(app_name="resume_rewrite", user_id="user_123", session_id=session_id)
    runner = Runner(agent=resume_analysis_agent, session_service=session_service, app_name="resume_rewrite")

    content_parts = [
        types.Part(text=(
            f"Perform a strategic analysis for resume {resume.id} against job url {job_description_url}. "
            f"Generate Markdown content for experience, skills, projects, education, and summary."
        ))
    ]

    content = types.Content(
        role='user',
        parts=content_parts
    )

    fragments = {}

    # Run the agent
    timeout_seconds = 600
    loop = asyncio.get_running_loop()
    start_time = loop.time()
    
    async for event in runner.run_async(new_message=content, session_id=session_id, user_id="user_123"):
        if loop.time() - start_time > timeout_seconds:
            logging.warning(f"⏰ Runner timeout of {timeout_seconds}s exceeded.")
            break
            
        if event.is_final_response() and event.content and event.content.parts:
            raw_text = event.content.parts[0].text.strip()
            logging.info(f"Agent Response from {event.author}: {raw_text[:100]}...")
            
            try:
                parsed = json.loads(raw_text)
                if isinstance(parsed, dict):
                    fragments.update(parsed)
            except json.JSONDecodeError:
                logging.error(f"Failed to parse JSON from {event.author}")

    return fragments
