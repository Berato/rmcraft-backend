"""
Cover Letter Analyst Agent

This agent analyzes a candidate's resume and job description to create
a strategic outline for a personalized cover letter.
"""

try:
    import os
    # Try to use real Google ADK by default, fall back to mock for testing
    if os.getenv('USE_MOCK_ADK', 'false').lower() == 'true':
        raise ImportError("Mock ADK forced for testing")
    from google.adk.agents import LlmAgent
    from google.adk.tools import FunctionTool
    from google.genai import types
    print("✅ Using real Google ADK")
except ImportError:
    print("⚠️ Google ADK not available, using mock implementation")
    # Import mock implementation
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from mock_adk import LlmAgent, FunctionTool
    # Mock types module
    import types

    class MockGenerateContentConfig:
        def __init__(self, temperature=0.1, response_mime_type=None, response_schema=None):
            self.temperature = temperature
            self.response_mime_type = response_mime_type
            self.response_schema = response_schema

    types.GenerateContentConfig = MockGenerateContentConfig
    types.Content = type('Content', (), {
        '__init__': lambda self, role, parts: None
    })
    types.Part = type('Part', (), {
        '__init__': lambda self, text=None, inline_data=None: None
    })

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import json
import re
from google.adk.planners import BuiltInPlanner
from app.agents.resume.strategic import search_agent_tool


def create_cover_letter_analyst_agent(resume_query_tool, job_description_query_tool):
    """
    Create the cover letter analyst agent that synthesizes JD + resume insights.

    Args:
        resume_query_tool: Function to query resume data from ChromaDB
        job_description_query_tool: Function to query job description data from ChromaDB

    Returns:
        LlmAgent configured for cover letter analysis
    """

    analyst_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="cover_letter_analyst_agent",
    description="Analyze resume, job description, and public profiles to create a strategic markdown blueprint.",
    instruction=(
        "## Persona ##"
        "\nYou are a Master Career Strategist and the lead agent in a multi-agent workflow. Your primary function is to conduct a comprehensive analysis and produce a detailed **Strategic Blueprint** in Markdown format. This document will serve as the single source of truth and instruction for all subsequent agents (like the Writer and Editor)."

        "\n\n## Goal ##"
        "\nYour goal is to synthesize information from a candidate's resume, a job description, and external research to create a rich, well-structured Markdown document. This document must not only outline the cover letter's content but also provide explicit instructions for other agents."

        "\n\n## Tools ##"
        "\nYou have access to three tools to conduct your research:"
        "\n1. `job_description_query_tool(queries: list[str])`: Use this to understand the **target**. Query it to extract key requirements, responsibilities, and keywords from the job description."
        "\n2. `resume_query_tool(queries: list[str])`: Use this to find the **internal evidence**. Query it to find the candidate's strongest qualifications, specific achievements, and skills from their resume."
        "\n3. `Google Search(query: str)`: Use this for **external context**. Query it to research the **company's** mission, values, or recent positive news. You can also use it to find the **candidate's public profiles** (like a personal website, portfolio, or technical blog) to find additional projects or evidence that strengthens their application."

        "\n\n## Process ##"
        "\n1. **Deconstruct the Role:** Use `job_description_query_tool` to identify the employer's critical needs."
        "\n2. **Research the Company:** Use `Google Search` to find key information for the 'Company Connection' section."
        "\n3. **Map Candidate's Strengths:** Use `resume_query_tool` to find specific, quantifiable achievements from the resume that directly map to the role's requirements. You can optionally supplement this by using `Google Search` to find relevant projects on the candidate's personal portfolio or blog."
        "\n4. **Construct the Blueprint:** Assemble all your findings into a detailed Markdown document using the structure specified in the 'Output Instructions'."

        "\n\n## Output Instructions ##"
        "\nCRITICAL: Your final output MUST be a single, comprehensive Markdown document. Do not use JSON. Structure the document with the following headers. Under each header, provide your analysis and explicit instructions for other agents inside blockquotes."
        
        "\n\n---"
        "\n\n# Cover Letter Strategic Blueprint"
        
        "\n\n## 1. Core Narrative & Goals"
        "\nSummarize the central theme of the cover letter. What is the one key message we want the hiring manager to remember?"
        "\n> **Instruction for Writer Agent:** This is the core story. Every paragraph you write should reinforce this central theme."
        
        "\n\n## 2. Target Role Analysis"
        "\nList the 3-5 most critical requirements and responsibilities extracted from the job description."
        "\n> **Instruction for Writer & Editor Agents:** Ensure the final letter directly addresses these specific points. These keywords should appear naturally in the text for ATS optimization."
        
        "\n\n## 3. Key Strengths & Evidence (from Resume & Web)"
        "\nList the candidate's strongest matching skills, projects, and experiences found in the resume or their public profiles. For each strength, provide the exact bullet point or project description as evidence."
        "\n- **Strength 1:** [e.g., Project Management, Client Tax Resolution, or Certified Crane Operation]"
        "\n  - **Evidence:** [e.g., 'Managed a 5-person crew to successfully complete the 12-story Riverfront tower project on time and under budget.']"
        "\n> **Instruction for Writer Agent:** These are your primary building blocks. Weave these specific examples into the body paragraphs to prove the candidate's capabilities."
        
        "\n\n## 4. Company Connection"
        "\nProvide 2-3 key points from your `Google Search` about the company's mission, values, or recent projects that align with the candidate's profile."
        "\n> **Instruction for Writer Agent:** Use these points to write a genuine 'Company Connection' paragraph that shows the candidate has done their research."

        "\n\n## 5. Strategic Outline"
        "\nProvide a detailed, point-by-point outline for the cover letter."
        "\n- **Opening Hook:** [e.g., Start by mentioning a major quantifiable achievement, like 'increased client retention by 15%' or 'completed the downtown project 3 weeks ahead of schedule'.]"
        "\n- **Body Paragraph 1 (Core Competency):** [e.g., Focus on a key skill like 'Corporate Tax Audits'. Detail the process, mentioning expertise in 'navigating IRS regulations' and 'utilizing Lacerte Tax Software'.]"
        "\n- **Body Paragraph 2 (Broader Impact):** [e.g., Discuss wider contributions like 'training junior staff on new safety protocols' or 'implementing a new inventory system that reduced material waste by 10%'.]"
        "\n- **Closing Paragraph:** [e.g., Reiterate the core value proposition and include a confident call-to-action.]"
        "\n> **Instruction for Writer Agent:** Follow this outline precisely to structure the letter."
        
        "\n\n## 6. Risk Mitigation"
        "\nIdentify any potential gaps (e.g., a missing required skill) and provide a brief strategy to address it (e.g., 'Focus on transferable skills from Project X to mitigate lack of direct experience in Y')."
        "\n> **Instruction for Writer Agent:** Subtly incorporate this mitigation strategy into the letter if necessary."

    ),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
    ),
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024
        )
    ),
    tools=[resume_query_tool, job_description_query_tool, search_agent_tool],
    )

    return analyst_agent


async def run_cover_letter_analysis(
    analyst_agent,
    resume_id: str,
    job_description_url: str,
    session_service,
    session_id: str,
    user_id: str = "user_123",
    optional_prompt: Optional[str] = None
):
    """
    Run the cover letter analysis using the analyst agent.

    Args:
        analyst_agent: The configured analyst agent
        resume_id: ID of the resume to analyze
        job_description_url: URL of the job description
        session_service: ADK session service
        session_id: Session ID for the agent run
        user_id: User ID for the session

    Returns:
        Dict containing the analysis results
    """

    from google.adk.runners import Runner

    # Create the session first
    session = await session_service.create_session(
        app_name="cover_letter_analysis",
        user_id=user_id,
        session_id=session_id
    )

    runner = Runner(agent=analyst_agent, session_service=session_service, app_name="cover_letter_analysis")

    content_parts = [
        types.Part(text=(
            f"Analyze resume {resume_id} and job description from {job_description_url} "
            f"to create a strategic cover letter outline. Focus on the candidate's strongest "
            f"qualifications and specific examples that match the job requirements."
            f"{f' Additional context (FROM THE USER DIRECTLY. USE THIS GUIDANCE IF PRESENT): {optional_prompt}' if optional_prompt else ''}"
        ))
    ]

    content = types.Content(
        role='user',
        parts=content_parts
    )

    analysis_result = None

    async for event in runner.run_async(new_message=content, session_id=session_id, user_id=user_id):
        if event.is_final_response() and event.content:
            if hasattr(event.content, 'parts') and event.content.parts:
                analysis_result = event.content.parts[0].text.strip()
                if analysis_result is not None:
                    print("✅ Cover letter analysis completed successfully")
                else:
                    print("❌ Failed to parse analysis result: Invalid JSON after cleanup")

    return analysis_result
