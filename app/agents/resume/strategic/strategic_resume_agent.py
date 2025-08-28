from google.adk.agents import ParallelAgent, SequentialAgent
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types
from google.adk.planners import BuiltInPlanner

import chromadb
from pyparsing import Any
import json
from app.services.resume_service import get_resume_pydantic
from app.tools.get_url_contents import get_url_contents
from app.schemas.ResumeSchemas import EducationAgentOutPutSchema, ExperienceAgentOutPutSchema, SkillsAgentOutPutSchema, ProjectsAgentOutPutSchema, ContactInfoAgentOutPutSchema, SummaryAgentOutPutSchema
import uuid


def process_resumes_for_chroma(resume_json: dict) -> tuple[list[str], list[dict], list[str]]:
    """
    Convert a resume JSON object into documents, metadatas and ids for ChromaDB.

    Returns:
      (documents, metadatas, ids)

    Expected resume_json shape (examples):
      {
        "summary": "string",
        "experience": [
          {
            "company": "Acme",
            "position": "Engineer",
            "startDate": "2020-01",
            "endDate": "2022-01",
            "responsibilities": ["did X", "did Y"]    # or a single string
          },
          ...
        ],
        "projects": [
          {"id": "p1", "name": "Proj", "description": "desc", "url": "http://..."},
          ...
        ],
        "skills": [
          {"name": "Python"}, ...
        ]
      }
    """

    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    # --- Process Experience ---
    for job in resume_json.get("experience", []):
        responsibilities = job.get("responsibilities", [])
        # Allow responsibilities to be a single string or a list
        if isinstance(responsibilities, str):
            responsibilities = [r.strip() for r in responsibilities.splitlines() if r.strip()]

        for responsibility in responsibilities:
            if not responsibility:
                continue  # Skip empty strings
            documents.append(responsibility)
            metadatas.append({
                "type": "experience",
                "company": job.get("company") or "Unknown Company",
                "position": job.get("position") or "Unknown Position",
                "startDate": job.get("startDate") or "Unknown",
                "endDate": job.get("endDate") or "Unknown"
            })
            ids.append(str(uuid.uuid4()))

    # --- Process Projects ---
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

    # --- Process Skills ---
    skill_list = [skill.get("name") for skill in resume_json.get("skills", []) if skill.get("name")]
    if skill_list:
        skill_summary = "Key technical skills include: " + ", ".join(skill_list)
        documents.append(skill_summary)
        metadatas.append({"type": "skills_summary"})
        ids.append("skills_summary_01")  # static ID for the summary doc

    # --- Process Summary ---
    if resume_json.get("summary"):
        documents.append(resume_json["summary"])
        metadatas.append({"type": "summary"})
        ids.append("main_summary_01")  # static ID for the main summary

    # Return the prepared data for Chroma insertion (caller will insert)
    return documents, metadatas, ids

async def strategic_resume_agent(resume_id: str, job_description_url: str):
  # Initialize ChromaDB client
  chroma_client = chromadb.EphemeralClient()

  resume_collection = chroma_client.get_or_create_collection(name="resume_parts")

  # Step 0 - Get resume parts and store them in ChromaDB
  resume = get_resume_pydantic(resume_id)
  if not resume:
    raise ValueError(f"Resume not found for id: {resume_id}")

  documents, metadatas, ids = process_resumes_for_chroma(resume.model_dump())
  resume_collection.add(documents=documents, metadatas=metadatas, ids=ids)

  # Step 1 - Fetch job description chunks and store in a temporary collection
  job_description_chunks = await get_url_contents(job_description_url)
  jd_collection = chroma_client.get_or_create_collection(name=f"jd_{str(uuid.uuid4())[:8]}")
  jd_collection.add(
    documents=job_description_chunks,
    metadatas=[{"source": job_description_url}] * len(job_description_chunks),
    ids=[str(uuid.uuid4()) for _ in job_description_chunks],
  )

  def resume_query_tool(queries: list[str], top_k: int = 4) -> list[dict]:
    resume_parts = []
    results = resume_collection.query(query_texts=queries, n_results=top_k)
    for doc, meta, score in zip(results.get('documents', []), results.get('metadatas', []), results.get('distances', [])):
      resume_parts.append({"document": doc, "metadata": meta, "score": score})
    return resume_parts

  def job_description_query_tool(queries: list[str], top_k: int = 10) -> list[dict]:
    jd_parts = []
    results = jd_collection.query(query_texts=queries, n_results=top_k)
    for doc, meta, score in zip(results.get('documents', []), results.get('metadatas', []), results.get('distances', [])):
      jd_parts.append({"document": doc, "metadata": meta, "score": score})
    return jd_parts

  # Build the experience-analysis agent with explicit JSON output instructions
  experience_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="experience_agent",
    description="Analyze resume + job description and extract relevant experience.",
    instruction=(
      "You are an expert resume analyst. Analyze the resume and job description and return ONLY a valid JSON object with the structure: {\"experiences\": []}. "
      "Each experience should have fields: id, company, position, startDate, endDate, and responsibilities (array of strings). "
      "Rewrite the experience descriptions to be more impactful and aligned with the job description."
      "Use the experience the best matches what the job description is asking for."
      "Do not include any other text, explanations, or markdown - only return the JSON object."
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.5),
    output_schema=ExperienceAgentOutPutSchema,
    output_key="experiences",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=1024)
    ),
    tools=[resume_query_tool, job_description_query_tool],
  )

  skills_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="skills_agent",
    description="Analyze resume + job description and extract relevant skills.",
    instruction=(
      "You are an expert skills analyst. Analyze the resume and job description and return ONLY a valid JSON object with the structure: {\"skills\": [], \"additional_skills\": []}. "
      "Each skill should have fields: id, name, and level (e.g., 'beginner', 'intermediate', 'expert'). "
      "Rewrite the skill descriptions to be more impactful and aligned with the job description."
      "Analyze all experience and projects to identify implicit skills that may not be explicitly listed but are relevant to the job description."
      "Search online if necessary to validate skill levels and descriptions."
      "Determine implicit skills level by analyzing projects and experience to determine how deeply the skill is embedded in the candidate's background."
      "Use the skills that best match what the job description is asking for."
      "Resumes have experience, skills, education, and projects sections so you can use all of them to identify relevant skills."
      "Any skills at beginner level will be included in the `additional_skills` property"
      "Do not include any other text, explanations, or markdown - only return the JSON object."
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.5),
    output_schema=SkillsAgentOutPutSchema,
    output_key="skills",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=1024)
    ),
  tools=[resume_query_tool, job_description_query_tool, google_search],
  )
  
  projects_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="projects_agent",
    description="Analyze resume + job description and extract relevant projects.",
    instruction=(
      "You are an expert projects analyst. Analyze the resume and job description and return ONLY a valid JSON object with the structure: {\"projects\": []}. "
      "Each project should have fields: id, name, description, url."
      "Rewrite the project descriptions to be more impactful and aligned with the job description."
      "Use the projects that best match what the job description is asking for."
      "Do not include any other text, explanations, or markdown - only return the JSON object."
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.5),
    output_schema=ProjectsAgentOutPutSchema,
    output_key="projects",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=1024)
    ),
    tools=[resume_query_tool, job_description_query_tool],
  )
  
  education_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="education_agent",
    description="Analyze resume + job description and extract relevant education.",
    instruction=(
      "Your only job is to extract the education information from the resume and present it in a structured format."
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
    output_schema=EducationAgentOutPutSchema,
    output_key="education",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=256)
    ),
    tools=[resume_query_tool],
  )

  contact_info_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="contact_info_agent",
    description="Analyze resume + job description and extract relevant contact information.",
    instruction=(
      "Your only job is to extract the contact information from the resume and present it in a structured format."
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
    output_schema=ContactInfoAgentOutPutSchema,
    output_key="contact_info",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=256)
    ),
    tools=[resume_query_tool],
  )

  resume_analysis_agent = ParallelAgent(
    name="resume_analysis_agent",
    description="Analyze resume and job description to extract relevant experiences and skills.",
    sub_agents=[
      experience_agent,
      skills_agent,
      projects_agent,
      education_agent,
      contact_info_agent
    ]
  )
  
  summary_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="summary_agent",
    description="Writes a professional summary for the resume that is relevant to the job description.",
    instruction=(
      "Your task is to generate a professional summary for the client based on the resume and job description analysis."
      "You will want to reference the summary in the resume itself so use the resume_query_tool to do so."
      "Ensure that the summary is concise and highlights the key qualifications and experiences relevant to the job description."
      "Use a google search if needed to supplement your knowledge."
      "Ensure it is ATS-compliant."
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.5),
    output_schema=SummaryAgentOutPutSchema,
    output_key="summary",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=1024)
    ),
  tools=[resume_query_tool, job_description_query_tool, google_search],

  )
  
  full_workflow = SequentialAgent(
    name="resume_analysis_workflow_agent",
    sub_agents=[resume_analysis_agent, summary_agent],
    description="Complete resume analysis workflow with parallel execution"
  )

  # Create a session and run the agent
  session_service = InMemorySessionService()
  session_id = uuid.uuid4().hex
  session = await session_service.create_session(app_name="resume_rewrite", user_id="user_123", session_id=session_id)
  runner = Runner(agent=full_workflow, session_service=session_service, app_name="resume_rewrite")

  content = types.Content(role='user', parts=[types.Part(text=f"Analyze resume {resume_id} and job description {job_description_url} and return JSON of relevant experiences, projects, and skills.")])

  # Prepare a merged final response structure that matches the agents' output schemas
  final_response = {
    "experiences": [],
    "skills": {"skills": [], "additional_skills": []},
    "projects": [],
    "education": [],
    "contact_info": [],
    "summary": ""
  }

  async for event in runner.run_async(new_message=content, session_id=session_id, user_id="user_123"):
    # Log events for debugging
    print(f"\n Debug Event: {event}")
    if event.is_final_response() and event.content:
      # If the event includes structured output with an output_key, merge it into the final_response
      if hasattr(event, 'output_key') and hasattr(event, 'output') and event.output_key:
        output_key = event.output_key
        output_val = event.output
        # If output is a pydantic model or similar, try to convert to plain dict
        try:
          if hasattr(output_val, 'model_dump'):
            output_val = output_val.model_dump()
        except Exception:
          pass

        # If the output is a dict that itself contains the expected key, prefer that nested shape
        if isinstance(output_val, dict) and output_key in output_val:
          final_response[output_key] = output_val[output_key]
        else:
          final_response[output_key] = output_val

        print(f"\n Structured Agent Response for key '{output_key}': {final_response[output_key]}")
      else:
        # Fallback to parsing text content (agent returned JSON/string)
        raw_text = event.content.parts[0].text.strip()
        print(f"\n Raw Agent Response: {raw_text}")
        try:
          parsed = json.loads(raw_text)
          # Merge top-level keys into final_response when possible
          if isinstance(parsed, dict):
            for k, v in parsed.items():
              final_response[k] = v
          else:
            # If parsed is a list or other shape, place it under experiences as a best-effort fallback
            # Normalize non-list parsed values into a single-item list so the schema stays consistent
            if isinstance(parsed, list):
              final_response["experiences"] = parsed
            else:
              final_response["experiences"] = [parsed]
        except Exception as e:
          print(f"\n JSON parsing failed: {e}")
          # leave final_response as the initialized, empty structure
      break

  # Ensure required keys exist and have sane defaults before returning
  final_response.setdefault("experiences", [])
  final_response.setdefault("skills", {"skills": [], "additional_skills": []})
  final_response.setdefault("projects", [])
  final_response.setdefault("education", [])
  final_response.setdefault("contact_info", [])
  final_response.setdefault("summary", "")

  return final_response
    # Step 1 - Take in the Job description link and extract relevant information (like title, company, description, requirements, responsibilities, skills, location, salary, source, url, createdAt) using Google Search API

    # Step 1.1 - Use Google Search API to find the job description

    # Step 1.2 - Extract relevant information from the job description

    # Step 2 - Find the most relevant experience, skills, projects and education from the resume that will match the job description

    # Use ChromaDB to search for relevant resume parts. We need to ensure the agent asks questions about the users experience, skills, projects and education to find the best matches.

    # We need to ensure the agent is looking at experience and the job description in order to rewrite the items with the most relevant information (It needs to pass ATS).
    # Additionally, the agent should consider the user's input and preferences when making suggestions.
    # The agent needs to ask clarifying questions to better understand the user's background and tailor the resume accordingly.

    # This is a list of the agents that will be needed to execute the plan:

    # Job Description Agent - Extracts and normalizes job description information
    # Resume Parsing Agent - Parses and normalizes resume information
    # Experience Matching Agent - Matches relevant experience to the job description
    # Skill Matching Agent - Matches relevant skills to the job description
    # Project Matching Agent - Matches relevant projects to the job description
    # Education Matching Agent - Matches relevant education to the job description

    # These can happen in parallel

    # Once these are done we need some creative agents to help rewrite the resume sections with the most relevant information. These are those agents:
    # Experience Rewriting Agent - Rewrites experience section to highlight relevant experience
    # Skill Rewriting Agent - Rewrites skills section to highlight relevant skills
    # Project Rewriting Agent - Rewrites projects section to highlight relevant projects
    # Education Rewriting Agent - Rewrites education section to highlight relevant education
    # Tone Adjustment Agent - Adjusts the tone of the resume to match the job description
    # Accuracy Agent - Ensures all information is accurate and no hallucinations are present. Will delegate fixes to other agents as needed.
    # Summary Rewriting Agent - Rewrites summary section to highlight relevant experience and skills and interest in the job