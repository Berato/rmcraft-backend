try:
    import os
    # Try to use real Google ADK by default, fall back to mock for testing
    if os.getenv('USE_MOCK_ADK', 'false').lower() == 'true':  # Changed default to 'false'
        raise ImportError("Mock ADK forced for testing")
    from google.adk.agents import ParallelAgent, SequentialAgent
    from google.adk.agents.llm_agent import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools import FunctionTool, google_search, agent_tool
    from google.genai import types
    from google.adk.planners import BuiltInPlanner
    print("✅ Using real Google ADK")
except ImportError:
    print("⚠️ Google ADK not available, using mock implementation")
    # Import mock implementation
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
    from mock_adk import (
        ParallelAgent, SequentialAgent, LlmAgent, Runner,
        InMemorySessionService, FunctionTool, google_search, agent_tool,
        BuiltInPlanner
    )
    # Mock types module
    import types
    types.GenerateContentConfig = type('GenerateContentConfig', (), {
        '__init__': lambda self, temperature=1, response_mime_type="application/json": None
    })
    types.ThinkingConfig = type('ThinkingConfig', (), {
        '__init__': lambda self, include_thoughts=False, thinking_budget=0: None
    })
    types.Content = type('Content', (), {
        '__init__': lambda self, role, parts: None
    })
    types.Part = type('Part', (), {
        '__init__': lambda self, text=None, inline_data=None: None
    })
    types.Blob = type('Blob', (), {
        '__init__': lambda self, mime_type, data: None
    })

import logging
import chromadb
from pyparsing import Any
import json
import asyncio
from app.agents import resume
from app.services.resume_service import get_resume_pydantic
from app.tools.get_url_contents import get_url_contents
from app.schemas.ResumeSchemas import EducationAgentOutPutSchema, ExperienceAgentOutPutSchema, ResumeResponse, SkillsAgentOutPutSchema, ProjectsAgentOutPutSchema, ContactInfoAgentOutPutSchema, SummaryAgentOutPutSchema
from app.agents.resume.strategic.schema_assembler import create_resume_from_fragments
import uuid
from google.adk.models.lite_llm import LiteLlm

OPENAI_MODEL = "openai/gpt-5-mini"
gpt5_model = "gemini-2.5-pro"  # Using Gemini 2.5 Pro for better performance


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


def validate_json_response(text: str, expected_keys: list = None) -> tuple[bool, str]:
  """
  Validate that the response is proper JSON and contains expected keys.
  Returns (is_valid, error_message)
  """
  try:
    parsed = json.loads(text)
    if not isinstance(parsed, dict):
      return False, "Response is not a JSON object"

    if expected_keys:
      missing_keys = [key for key in expected_keys if key not in parsed]
      if missing_keys:
        return False, f"Missing expected keys: {missing_keys}"

    return True, ""
  except json.JSONDecodeError as e:
    return False, f"Invalid JSON: {str(e)}"
  except Exception as e:
    return False, f"Unexpected error: {str(e)}"


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
  model="gemini-2.5-flash",
  name="search_agent", 
  description="Performs internet searches using Google Search to find current information.",
  instruction=(
    "You are a search specialist agent. When given a search query, use the google_search tool to find relevant information. "
    "Return the search results in a clear, structured format that other agents can easily use. "
    "Focus on providing factual, current information from reliable sources."
  ),
  generate_content_config=types.GenerateContentConfig(
    temperature=1
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

async def strategic_resume_agent(
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

  # Build the experience-analysis agent with creative analysis focus
  experience_test_agent = LlmAgent(
    model=gpt5_model,
    name="experience_agent",
    description="Analyze resume + job description and extract relevant experience with creative insights and JSON output.",
instruction=(
    "## Persona ##"
    "\nYou are an expert Resume Strategist and Editor. You specialize in selecting a candidate's most relevant work experiences and tailoring the language to perfectly match the requirements of a specific job description."

    "\n\n## Goal ##"
    "\nYour goal is to analyze a job description and a candidate's full work history to produce a curated list of the most relevant professional experiences. The responsibilities for each experience must be edited to highlight the skills and achievements that directly align with the target job. The final output must be a structured JSON object."

    "\n\n## Tools ##"
    "\n- `job_description_query_tool(queries: list[str])`: Use this tool to understand the **target**. Identify the key responsibilities, required skills, and keywords from the job description."
    "\n- `resume_query_tool(queries: list[str])`: Use this tool to find the **evidence**. After analyzing the job description, use relevant keywords to search the candidate's full work history for matching experiences and achievements."

    "\n\n## Process ##"
    "\n1. **Analyze the Job:** First, use the `job_description_query_tool` to determine the most important qualifications and duties for the role."
    "\n2. **Select Relevant Experience:** Use the keywords from your analysis to query the candidate's history with `resume_query_tool`. Identify the 2-4 most relevant past jobs to include in the tailored resume."
    "\n3. **Tailor the Content:** For each selected job, review its responsibilities. Edit and rephrase the bullet points to use language and keywords from the job description. Focus on highlighting quantifiable achievements and direct skill matches."
    "\n4. **Format the Output:** Assemble the curated and edited experiences into the final JSON structure. Generate a new, unique ID for each experience entry (e.g., 'exp_1', 'exp_2')."

    "\n\n## Critical Rules ##"
    "\n- **Input:** Ignore any images that may be part of the input; focus only on the text data available through your tools."
    "\n- **Output:** Your final response MUST be a single, valid JSON object"
    f"\n JSON Schema: \n {ExperienceAgentOutPutSchema.model_json_schema()}" 
    ),
    generate_content_config=types.GenerateContentConfig(
      temperature=0.7
    ),
    output_schema=ExperienceAgentOutPutSchema,
    output_key="experiences",
    tools=[resume_query_tool, job_description_query_tool],
  )


  skills_agent = LlmAgent(
    model=gpt5_model,
    name="skills_agent",
    description="Analyze resume + job description and extract relevant skills with strategic insights and JSON output.",
# First, ensure the schema is available in the scope where you define the agent.
# from app.schemas.ResumeSchemas import ExperienceAgentOutPutSchema

instruction=(
    "## Persona ##"
    "\nYou are an expert Resume Strategist and Editor. You specialize in selecting a candidate's most relevant work experiences and tailoring the language to perfectly match the requirements of a specific job description."

    "\n\n## Goal ##"
    "\nYour goal is to analyze a job description and a candidate's full work history to produce a curated list of the most relevant professional experiences. The responsibilities for each experience must be edited to highlight the skills and achievements that directly align with the target job. The final output must be a structured JSON object."

    "\n\n## Tools ##"
    "\n- `job_description_query_tool(queries: list[str])`: Use this tool to understand the **target**. Identify the key responsibilities, required skills, and keywords from the job description."
    "\n- `resume_query_tool(queries: list[str])`: Use this tool to find the **evidence**. After analyzing the job description, use relevant keywords to search the candidate's full work history for matching experiences and achievements."
    "\n- `search_agent_tool(queries: list[str])`: Use this tool to find additional context or information that may be relevant to the analysis."

    "\n\n## Process ##"
    "\n1. **Analyze the Job:** First, use the `job_description_query_tool` to determine the most important qualifications and duties for the role."
    "\n2. **Select Relevant Experience:** Use the keywords from your analysis to query the candidate's history with `resume_query_tool`. Identify the 2-4 most relevant past jobs to include in the tailored resume."
    "\n3. **Tailor the Content:** For each selected job, review its responsibilities. Edit and rephrase the bullet points to use language and keywords from the job description. Focus on highlighting quantifiable achievements and direct skill matches."
    "\n4. **Format the Output:** Assemble the curated and edited experiences into the final JSON structure. Generate a new, unique ID for each experience entry (e.g., 'exp_1', 'exp_2')."

    "\n\n## Critical Rules ##"
    "\n- **Input:** Ignore any images that may be part of the input; focus only on the text data available through your tools."
    "\n- **Output:** Your final response MUST be a single, valid JSON object that matches the `ExperienceAgentOutPutSchema`. Do not include markdown fences or any other text. Ensure every experience object in the final array has a unique `id` field."
    
    # --- ADDED AS REQUESTED ---
    f"\n\n## REQUIRED JSON SCHEMA ##\n```json\n{SkillsAgentOutPutSchema.model_json_schema()}\n```"
),
    generate_content_config=types.GenerateContentConfig(
      temperature=0.7
    ),
    output_schema=SkillsAgentOutPutSchema,
    output_key="skills",
    tools=[resume_query_tool, job_description_query_tool, search_agent_tool],
  )

  projects_agent = LlmAgent(
    model=gpt5_model,
    name="projects_agent",
    description="Analyze resume + job description and extract relevant projects with creative insights and JSON output.",
# First, ensure the schema is available in the scope where you define the agent.
# from app.schemas.ResumeSchemas import ProjectsAgentOutPutSchema

instruction=(
    "## Persona ##"
    "\nYou are an expert Project Strategist. You excel at identifying a candidate's key projects and reframing their descriptions to powerfully demonstrate their value for a specific job opportunity."

    "\n\n## Goal ##"
    "\nYour goal is to analyze a job description and a candidate's portfolio of projects to produce a curated list of their most relevant projects. The description for each project must be edited to highlight the skills and outcomes that directly align with the target job. The final output must be a structured JSON object."

    "\n\n## Tools ##"
    "\n- `job_description_query_tool(queries: list[str])`: Use this tool to understand the **target**. Identify the key technologies, methodologies, and desired outcomes mentioned in the job description."
    "\n- `resume_query_tool(queries: list[str])`: Use this tool to find the **evidence**. After analyzing the job description, search the candidate's full list of projects to find those that best demonstrate the required skills."

    "\n\n## Process ##"
    "\n1. **Analyze the Job:** Use `job_description_query_tool` to determine the most important skills and project types the employer is looking for (e.g., 'experience with data migration projects', 'agile development')."
    "\n2. **Select Relevant Projects:** Use the keywords from your analysis to query the candidate's history with `resume_query_tool`. Identify the 2-3 most impactful projects to feature."
    "\n3. **Tailor the Descriptions:** For each selected project, rewrite its description. Emphasize the aspects that align with the job description. Use keywords from the job description and focus on the project's business impact or technical achievements."
    "\n4. **Format the Output:** Assemble the curated and edited projects into the final JSON structure. Generate a new, unique ID for each project (e.g., 'proj_1'). If a project URL is not available, set the 'url' field to an empty string."

    "\n\n## Critical Rules ##"
    "\n- **Input:** Ignore any images that may be part of the input; focus only on the text data available through your tools."
    "\n- **Output:** Your final response MUST be a single, valid JSON object that matches the `ProjectsAgentOutPutSchema`. Do not include markdown fences or any other text. Ensure every project object in the final array has a unique `id` field."
    
    f"\n\n## REQUIRED JSON SCHEMA ##\n```json\n{ProjectsAgentOutPutSchema.model_json_schema()}\n```"
    ),
    generate_content_config=types.GenerateContentConfig(
      temperature=0.7
    ),
    output_schema=ProjectsAgentOutPutSchema,
    output_key="projects",
    tools=[resume_query_tool, job_description_query_tool],
  )
  
  summary_agent = LlmAgent(
    model=gpt5_model,
    name="summary_agent",
    description="Write a creative, compelling professional summary for the resume with JSON output.",
    # First, ensure the schema is available in the scope where you define the agent.
# from app.schemas.ResumeSchemas import SummaryAgentOutPutSchema

instruction=(
    "## Persona ##"
    "\nYou are an expert Career Storyteller and Resume Writer. Your superpower is distilling a candidate's entire career into a powerful, concise, and compelling professional summary."

    "\n\n## Goal ##"
    "\nYour goal is to write a 3-5 sentence professional summary that serves as the 'elevator pitch' at the top of a resume. This summary must be tailored to a specific job description, highlighting the candidate's most impressive and relevant qualifications. The final output must be a structured JSON object."

    "\n\n## Tools ##"
    "\n- `job_description_query_tool(queries: list[str])`: Use this to identify the **most critical keywords and qualifications** the employer is seeking."
    "\n- `resume_query_tool(queries: list[str])`: Use this to find the **candidate's peak achievements**. Look for quantifiable results, key projects, and top-level skills that match the job."
    "\n- `search_agent_tool(query: str)`: (Optional) Use this to quickly understand the company's industry or mission to add a relevant keyword (e.g., 'passionate about renewable energy')."

    "\n\n## Process ##"
    "\n1. **Identify Core Keywords:** Use the `job_description_query_tool` to find the top 3-4 keywords or phrases (e.g., 'senior project manager', 'data-driven decision making')."
    "\n2. **Find Peak Achievements:** Use the `resume_query_tool` to find the most impressive, quantifiable achievements from the candidate's experience and projects (e.g., 'led a team of 10', 'increased efficiency by 25%')."
    "\n3. **Synthesize the Narrative:** Combine the keywords and achievements into a compelling 3-5 sentence narrative. Start with the candidate's title and years of experience, follow with 1-2 key accomplishments, mention core skills, and end with a statement about their professional goals as they relate to the company."
    "\n4. **Format the Output:** Place the final, polished summary string into the required JSON structure."

    "\n\n## Critical Rules ##"
    "\n- **Input:** Ignore any images that may be part of the input; focus only on the text data available through your tools."
    "\n- **Tone:** The tone must be confident, professional, and personable."
    "\n- **Output:** Your final response MUST be a single, valid JSON object that matches the `SummaryAgentOutPutSchema`. Do not include markdown fences or any other text."
    
    f"\n\n## REQUIRED JSON SCHEMA ##\n```json\n{SummaryAgentOutPutSchema.model_json_schema()}\n```"
    ),
    generate_content_config=types.GenerateContentConfig(
      temperature=0.8
    ),
    output_schema=SummaryAgentOutPutSchema,
    output_key="summary",
    tools=[resume_query_tool, job_description_query_tool, search_agent_tool],
  )



  # Run analysis agents in parallel (experience, skills, projects)
  resume_analysis_agent = ParallelAgent(
    name="resume_analysis_agent",
    description="Analyze resume and job description to extract relevant experiences, skills, and projects.",
    sub_agents=[
      experience_test_agent,
      skills_agent,
      projects_agent
    ]
  )
  full_workflow = SequentialAgent(
    name="full_resume_workflow",
    sub_agents=[
        resume_analysis_agent,
        summary_agent
    ],
    description="Complete resume analysis and summary workflow."
  )

  # Create a session and run the agent
  session_service = InMemorySessionService()
  session_id = uuid.uuid4().hex
  session = await session_service.create_session(app_name="resume_rewrite", user_id="user_123", session_id=session_id)
  runner = Runner(agent=full_workflow, session_service=session_service, app_name="resume_rewrite")

  content_parts = [
      types.Part(text=(
          f"Perform a strategic analysis for resume {resume.id} against job url {job_description_url}. "
          f"Extract and analyze relevant experience, skills, projects, and create a compelling summary."
      ))
  ]

  content = types.Content(
      role='user',
      parts=content_parts
  )

  # Collect agent outputs into fragments for schema assembler
  fragments = {
    "experience": [],
    "skills": {"skills": [], "additional_skills": []},
    "projects": [],
    "education": {"education": education_data},  # Wrap in expected dict format
    "contact_info": {"contact_info": contact_info_data},  # Wrap in expected dict format
    "summary": ""
  }

  # Ensure a name fragment is present. Prefer resume.name, fall back to personalInfo first/last name, else empty string.
  name_value = ""
  try:
    if hasattr(resume, 'name') and resume.name:
      name_value = resume.name
    elif hasattr(resume, 'personalInfo') and resume.personalInfo:
      personal = resume.personalInfo
      if isinstance(personal, dict):
        first = personal.get('firstName', '')
        last = personal.get('lastName', '')
        name_value = (first + ' ' + last).strip() if (first or last) else ''
      elif hasattr(personal, 'model_dump'):
        pd = personal.model_dump()
        first = pd.get('firstName', '')
        last = pd.get('lastName', '')
        name_value = (first + ' ' + last).strip() if (first or last) else ''
  except Exception:
    name_value = ""

  fragments["name"] = {"name": name_value}

  # Run the agent with a safety timeout to avoid indefinite hangs when models return
  # non-final events (e.g., function_calls) or when downstream services are slow.
  timeout_seconds = 60
  loop = asyncio.get_running_loop()
  start_time = loop.time()
  async for event in runner.run_async(new_message=content, session_id=session_id, user_id="user_123"):
    # Enforce timeout
    if loop.time() - start_time > timeout_seconds:
      print(f"⏰ Runner timeout of {timeout_seconds}s exceeded, aborting agent run.")
      break
      
    if event.is_final_response() and event.content:
      # With structured output, the content should be valid JSON
      if hasattr(event.content, 'parts') and event.content.parts:
        raw_text = event.content.parts[0].text.strip()
        logging.info(f"\n🔄 Agent Response: {raw_text}")
        logging.info(f"Event Parts: {event.content.parts}")

        try:
          # Parse the structured JSON response
          parsed_response = json.loads(raw_text)
          logging.info(f"✅ Parsed structured response: {type(parsed_response)}")
          
          # Map structured responses to fragments
          if isinstance(parsed_response, dict):
            for key, value in parsed_response.items():
              if key in fragments:
                fragments[key] = value
                print(f"✅ Updated fragment '{key}' with structured data")
          
        except json.JSONDecodeError as e:
          print(f"❌ JSON parsing failed: {e}")
          print(f"Raw response was: {raw_text}")
          
          # Try manual extraction as fallback
          cleaned_text = clean_json_response(raw_text)
          try:
            parsed = json.loads(cleaned_text)
            if isinstance(parsed, dict):
              for k, v in parsed.items():
                if k in fragments:
                  fragments[k] = v
                  print(f"⚠️ Fallback: Updated fragment '{k}' with cleaned data")
          except json.JSONDecodeError:
            print(f"❌ Fallback parsing also failed for: {cleaned_text}")
      else:
        print(f"⚠️ Event has no content parts: {event}")
    else:
      if hasattr(event, 'is_final_response'):
        print(f"⚠️ Non-final event: is_final={event.is_final_response()}, has_content={bool(getattr(event, 'content', None))}")
      else:
        print(f"⚠️ Event without final response check: {type(event)}")

  # Use schema assembler to validate, repair, and build final response
  final_response, diagnostics = create_resume_from_fragments(fragments)
  logging.info(f"Final response: {final_response}")
  logging.info(f"Diagnostics: {diagnostics}")
  logging.info(f"Session: {session.state}")
  # Log diagnostics for monitoring
  for diagnostic in diagnostics:
    if diagnostic.status == "FAILED":
      print(f"❌ Schema repair failed for {diagnostic.field}: {diagnostic.error_message}")
    elif diagnostic.repairs_applied:
      print(f"⚠️ Schema repair applied for {diagnostic.field}: {', '.join(diagnostic.repairs_applied)}")
    else:
      print(f"✅ Schema validation passed for {diagnostic.field}")

  return final_response