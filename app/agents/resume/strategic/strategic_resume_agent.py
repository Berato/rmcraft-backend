from google.adk.agents import ParallelAgent, SequentialAgent
from google.adk.agents.llm_agent import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool, google_search, agent_tool
from google.genai import types
from google.adk.planners import BuiltInPlanner

import chromadb
from pyparsing import Any
import json
from app.services.resume_service import get_resume_pydantic
from app.tools.get_url_contents import get_url_contents
from app.schemas.ResumeSchemas import EducationAgentOutPutSchema, ExperienceAgentOutPutSchema, SkillsAgentOutPutSchema, ProjectsAgentOutPutSchema, ContactInfoAgentOutPutSchema, SummaryAgentOutPutSchema
import uuid





def clean_json_response(raw_text: str) -> str:
  """
  Clean raw LLM response by removing markdown formatting and extracting pure JSON.
  Handles cases where LLM returns JSON wrapped in markdown code blocks.
  """
  if not raw_text:
    return raw_text

  # Remove markdown code block markers
  text = raw_text.strip()
  if text.startswith('```json'):
    text = text[7:]
  elif text.startswith('```'):
    text = text[3:]

  if text.endswith('```'):
    text = text[:-3]

  # Remove any leading/trailing whitespace and newlines
  text = text.strip()

  # If the text starts with markdown headers or explanatory text, try to find JSON
  if not text.startswith('{'):
    # Look for JSON object in the text
    start_idx = text.find('{')
    end_idx = text.rfind('}')
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
      text = text[start_idx:end_idx + 1]

  return text


async def fetch_jd_chunks(url: str, tool_context: object | None = None) -> dict:
  """Fetch and return job-description chunks for a given URL.

  This wrapper calls the repo's async `get_url_contents` helper and returns a
  dict with status and chunks so it is easy for agents to consume.
  """
  chunks = await get_url_contents(url)
  return {"status": "success", "chunks": chunks, "source": url}


# FunctionTool instance agents can call inside sub-agents (allowed by ADK)
fetch_jd_tool = FunctionTool(func=fetch_jd_chunks)


# Create a dedicated search agent using built-in google_search (root-level only)
search_agent = LlmAgent(
  model="gemini-2.0-flash",
  name="search_agent", 
  description="Performs internet searches using Google Search to find current information.",
  instruction=(
    "You are a search specialist agent. When given a search query, use the google_search tool to find relevant information. "
    "Return the search results in a clear, structured format that other agents can easily use. "
    "Focus on providing factual, current information from reliable sources."
  ),
  tools=[google_search],
)

# Expose the search agent as an AgentTool so other agents can call it
search_agent_tool = agent_tool.AgentTool(agent=search_agent)


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

    # --- Process Education ---
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

    # --- Process Contact Information ---
    contact_info = resume_json.get("personalInfo", {})
    if contact_info:
        contact_parts = []
        if contact_info.get("email"):
            contact_parts.append(f"Email: {contact_info['email']}")
        if contact_info.get("phone"):
            contact_parts.append(f"Phone: {contact_info['phone']}")
        if contact_info.get("linkedin"):
            contact_parts.append(f"LinkedIn: {contact_info['linkedin']}")
        if contact_info.get("github"):
            contact_parts.append(f"GitHub: {contact_info['github']}")
        if contact_info.get("website"):
            contact_parts.append(f"Website: {contact_info['website']}")

        if contact_parts:
            contact_summary = "Contact information: " + ", ".join(contact_parts)
            documents.append(contact_summary)
            metadatas.append({"type": "contact_info"})
            ids.append("contact_info_01")  # static ID for contact info

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

  # Extract education and contact info directly from resume
  education_data = resume.education if hasattr(resume, 'education') and resume.education else []
  contact_info_data = []
  if hasattr(resume, 'personalInfo') and resume.personalInfo:
    # Convert personalInfo to the expected contact_info format
    personal_info = resume.personalInfo
    if isinstance(personal_info, dict):
      contact_info_data = [{
        "email": personal_info.get("email", ""),
        "phone": personal_info.get("phone", ""),
        "linkedin": personal_info.get("linkedin", ""),
        "github": personal_info.get("github", ""),
        "website": personal_info.get("website", "")
      }]
    elif hasattr(personal_info, 'model_dump'):
      contact_dict = personal_info.model_dump()
      contact_info_data = [{
        "email": contact_dict.get("email", ""),
        "phone": contact_dict.get("phone", ""),
        "linkedin": contact_dict.get("linkedin", ""),
        "github": contact_dict.get("github", ""),
        "website": contact_dict.get("website", "")
      }]

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

  # Build the experience-analysis agent with creative analysis focus
  experience_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="experience_agent",
    description="Analyze resume + job description and extract relevant experience with creative insights and JSON output.",
    instruction=(
      "You are an expert resume strategist. Analyze the resume and job description data. "
      "Your response must be ONLY a valid JSON object - no text before or after. "
      "Return this exact structure: {\"experiences\": [{\"id\": \"exp_1\", \"company\": \"Company Name\", \"position\": \"Job Title\", \"startDate\": \"2020-01\", \"endDate\": \"Present\", \"responsibilities\": [\"Responsibility 1\", \"Responsibility 2\"]}]} "
      "Use resume_query_tool to get experience data. Start your response with { and end with }"
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
    output_schema=ExperienceAgentOutPutSchema,
    output_key="experiences",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=0)
    ),
    tools=[resume_query_tool, job_description_query_tool],
  )

    # Build the summary structure agent to format creative summary into JSON
  summary_structure_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="summary_structure_agent",
    description="Extract and format summary data into clean JSON structure.",
    instruction=(
      "You are a JSON formatting specialist. Your task is to analyze the resume and job description data and return ONLY a valid JSON object. "
      "Use the resume_query_tool and job_description_query_tool to gather the same information that the creative agent would use. "
      "CRITICAL REQUIREMENTS: "
      "- Return ONLY the JSON object with NO additional text, explanations, markdown, or formatting. "
      "- Do NOT include any markdown code blocks (```json or ```). "
      "- Do NOT include any headers, comments, or explanatory text. "
      "- Do NOT use triple backticks or any other markdown syntax. "
      "- Start your response directly with the opening brace { and end with the closing brace }. "
      "The JSON structure must be exactly: {\"summary\": \"your summary text here\"}. "
      "Do NOT include any markdown code blocks, headers, or explanatory text. "
      "Start your response directly with the opening brace { and end with the closing brace }."
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
    output_schema=SummaryAgentOutPutSchema,
    output_key="summary",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=0)
    ),  # Minimal thinking config for pure formatting
    tools=[resume_query_tool, job_description_query_tool, search_agent_tool],  # Give access to same tools
  )

  skills_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="skills_agent",
    description="Analyze resume + job description and extract relevant skills with strategic insights and JSON output.",
    instruction=(
      "You are an expert skills strategist. Analyze the resume and job description data. "
      "Your response must be ONLY a valid JSON object - no text before or after. "
      "Return this exact structure: {\"skills\": [{\"id\": \"skill_1\", \"name\": \"Skill Name\", \"level\": 3}], \"additional_skills\": [\"Basic Skill 1\", \"Basic Skill 2\"]} "
      "Use resume_query_tool to get skills data. Start your response with { and end with }"
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
    output_schema=SkillsAgentOutPutSchema,
    output_key="skills",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=0)
    ),
    tools=[resume_query_tool, job_description_query_tool, search_agent_tool],
  )

  projects_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="projects_agent",
    description="Analyze resume + job description and extract relevant projects with creative insights and JSON output.",
    instruction=(
      "You are an expert project strategist. Analyze the resume and job description data. "
      "Your response must be ONLY a valid JSON object - no text before or after. "
      "Return this exact structure: {\"projects\": [{\"id\": \"proj_1\", \"name\": \"Project Name\", \"description\": \"Project description\", \"url\": \"https://example.com\"}]} "
      "Use resume_query_tool to get project data. Start your response with { and end with }"
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
    output_schema=ProjectsAgentOutPutSchema,
    output_key="projects",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=0)
    ),
    tools=[resume_query_tool, job_description_query_tool],
  )

  # Build the projects structure agent to format creative analysis into JSON
  projects_structure_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="projects_structure_agent",
    description="Extract and format projects data into clean JSON structure.",
    instruction=(
      "JSON ONLY. No text. No explanations. No markdown. "
      "Return: {\"projects\": [{\"id\": \"proj_1\", \"name\": \"Project\", \"description\": \"Description\", \"url\": \"https://example.com\"}]} "
      "Use resume_query_tool to get data. Start with { end with }"
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.0),
    output_schema=ProjectsAgentOutPutSchema,
    output_key="projects",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=0)
    ),  # Minimal thinking config for pure formatting
    tools=[resume_query_tool],  # Only need resume data
  )
  
  summary_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="summary_agent",
    description="Write a creative, compelling professional summary for the resume with JSON output.",
    instruction=(
      "You are an expert career storyteller. Analyze the resume and job description data. "
      "Your response must be ONLY a valid JSON object - no text before or after. "
      "Return this exact structure: {\"summary\": \"your complete summary text here\"} "
      "Use resume_query_tool to get summary data. Start your response with { and end with }"
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
    output_schema=SummaryAgentOutPutSchema,
    output_key="summary",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=0)
    ),
    tools=[resume_query_tool, job_description_query_tool, search_agent_tool],
  )

  # Build the summary structure agent to format creative summary into JSON
  summary_structure_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="summary_structure_agent",
    description="Extract and format summary data into clean JSON structure.",
    instruction=(
      "You are a JSON formatting specialist. Your task is to analyze the resume and job description data and return ONLY a valid JSON object. "
      "Use the resume_query_tool and job_description_query_tool to gather the same information that the creative agent would use. "
      "CRITICAL REQUIREMENTS: "
      "- Return ONLY the JSON object with NO additional text, explanations, markdown, or formatting. "
      "- Do NOT include any markdown code blocks (```json or ```). "
      "- Do NOT include any headers, comments, or explanatory text. "
      "- Do NOT use triple backticks or any other markdown syntax. "
      "- Start your response directly with the opening brace { and end with the closing brace }. "
      "The JSON structure must be exactly: {\"summary\": \"your summary text here\"}. "
      "Do NOT include any markdown code blocks, headers, or explanatory text. "
      "Start your response directly with the opening brace { and end with the closing brace }."
    ),
    generate_content_config=types.GenerateContentConfig(temperature=0.1),
    output_schema=SummaryAgentOutPutSchema,
    output_key="summary",
    planner=BuiltInPlanner(
      thinking_config=types.ThinkingConfig(include_thoughts=False, thinking_budget=0)
    ),  # Minimal thinking config for pure formatting
    tools=[resume_query_tool, job_description_query_tool, search_agent_tool],  # Give access to same tools
  )
  
  # Run analysis agents in parallel (experience, skills, projects)
  resume_analysis_agent = ParallelAgent(
    name="resume_analysis_agent",
    description="Analyze resume and job description to extract relevant experiences, skills, and projects.",
    sub_agents=[
      experience_agent,
      skills_agent,
      projects_agent
    ]
  )
  full_workflow = SequentialAgent(
    name="resume_analysis_workflow_agent",
    sub_agents=[resume_analysis_agent, summary_agent],
    description="Complete resume analysis workflow with parallel execution and creative summary"
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
    "education": education_data,
    "contact_info": contact_info_data,
    "summary": ""
  }

  async for event in runner.run_async(new_message=content, session_id=session_id, user_id="user_123"):
    # Log events for debugging
    print(f"\n Debug Event: {event}")
    if event.is_final_response() and event.content:
      # Initialize output_key to handle cases where it's not present
      output_key = None
      
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
          # Clean the raw text to remove markdown formatting
          cleaned_text = clean_json_response(raw_text)
          print(f"\n Cleaned Agent Response: {cleaned_text}")

          parsed = json.loads(cleaned_text)
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
          print(f"Raw response was: {raw_text}")
          print(f"Cleaned response was: {cleaned_text}")
          # For contact_info, return empty list if parsing fails
          if output_key == "contact_info":
            final_response[output_key] = []
          elif output_key == "education":
            final_response[output_key] = []
          # leave final_response as the initialized, empty structure for other keys

  # Ensure required keys exist and have sane defaults before returning
  final_response.setdefault("experiences", [])
  final_response.setdefault("skills", {"skills": [], "additional_skills": []})
  final_response.setdefault("projects", [])
  final_response.setdefault("education", [])
  final_response.setdefault("contact_info", [])
  final_response.setdefault("summary", "")

  return final_response