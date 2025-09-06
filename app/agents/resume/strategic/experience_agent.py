"""
Isolated Experience Agent

Builds and runs only the experience-focused agent with the same tools
as in the strategic agent, but without any JSON formatting or extra agents.
"""

from __future__ import annotations

import uuid
import logging
import chromadb
from typing import Optional
from google.adk.planners import BuiltInPlanner
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prefer real Google ADK, but fall back to mock if unavailable (for tests/dev)
try:
	import os
	if os.getenv("USE_MOCK_ADK", "false").lower() == "true":
		raise ImportError("Mock ADK forced for testing")
	from google.adk.agents.llm_agent import LlmAgent
	from google.adk.runners import Runner
	from google.adk.sessions import InMemorySessionService
	from google.genai import types
	from google.adk.models.lite_llm import LiteLlm
    
	REAL_ADK = True
except ImportError:  # pragma: no cover - enable running without Google ADK
	REAL_ADK = False
	import sys, os
	sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))))
	from mock_adk import (
		LlmAgent, Runner, InMemorySessionService,
	)
	# Minimal mock types compatible with our usage
	import types as _types
	types = _types
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
	from google.adk.models.lite_llm import LiteLlm  # provided by mock in tests

from app.models import resume
from app.tools.get_url_contents import get_url_contents
from app.schemas.ResumeSchemas import ResumeResponse


OPENAI_MODEL = "openai/gpt-5-mini"
gpt5_model = LiteLlm(model=OPENAI_MODEL)


def process_resumes_for_chroma(resume_json: dict) -> tuple[list[str], list[dict], list[str]]:
	"""
	Convert a resume JSON object into documents, metadatas and ids for ChromaDB.

	Returns: (documents, metadatas, ids)
	"""
	documents: list[str] = []
	metadatas: list[dict] = []
	ids: list[str] = []

	# Experience responsibilities
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
				"endDate": job.get("endDate") or "Unknown",
			})
			ids.append(str(uuid.uuid4()))

	# Projects (compact)
	for project in resume_json.get("projects", []):
		name = project.get("name", "") or ""
		desc = project.get("description", "") or ""
		doc_content = f"{name}: {desc}".strip(": ").strip()
		if not doc_content:
			continue
		documents.append(doc_content)
		metadatas.append({"type": "project", "name": project.get("name") or "Unknown Project"})
		ids.append(project.get("id") or str(uuid.uuid4()))

	# Skills summary
	skill_list = [s.get("name") for s in resume_json.get("skills", []) if s.get("name")]
	if skill_list:
		documents.append("Key technical skills include: " + ", ".join(skill_list))
		metadatas.append({"type": "skills_summary"})
		ids.append("skills_summary_01")

	# Summary
	if resume_json.get("summary"):
		documents.append(resume_json["summary"])
		metadatas.append({"type": "summary"})
		ids.append("main_summary_01")

	# Education
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
			"endDate": education.get("endDate") or "Unknown",
		})
		ids.append(education.get("id") or str(uuid.uuid4()))

	# Contact info
	contact_info = resume_json.get("personalInfo", {})
	if contact_info:
		parts = []
		if contact_info.get("email"): parts.append(f"Email: {contact_info['email']}")
		if contact_info.get("phone"): parts.append(f"Phone: {contact_info['phone']}")
		if contact_info.get("linkedin"): parts.append(f"LinkedIn: {contact_info['linkedin']}")
		if contact_info.get("github"): parts.append(f"GitHub: {contact_info['github']}")
		if contact_info.get("website"): parts.append(f"Website: {contact_info['website']}")
		if parts:
			documents.append("Contact information: " + ", ".join(parts))
			metadatas.append({"type": "contact_info"})
			ids.append("contact_info_01")

	return documents, metadatas, ids


async def experience_agent_isolated(
	resume: ResumeResponse,
	job_description_url: str,
	prompt: Optional[str] = None,
) -> str:
	"""Run the isolated experience agent and return the final plain-text response."""
	if not resume:
		raise ValueError("Resume is required")

	try:
		# Initialize ChromaDB client (same pattern as strategic_resume_agent)
		chroma_client = chromadb.EphemeralClient()
		resume_collection = chroma_client.get_or_create_collection(name="resume_parts")

		logging.info("Indexing resume into ChromaDB")
		documents, metadatas, ids = process_resumes_for_chroma(resume.model_dump())
		if not documents:
			raise ValueError("No resume data found to process; cancelling the process.")
		resume_collection.add(documents=documents, metadatas=metadatas, ids=ids)
	except Exception as e:
		logging.error(f"Error processing resume into ChromaDB: {e}")
		raise ValueError(f"Failed to process resume: {e}")

	try:
		# Job description chunks -> temp collection
		logging.info("Fetching job description")
		jd_chunks = await get_url_contents(job_description_url)
		jd_collection = chroma_client.get_or_create_collection(name=f"jd_{str(uuid.uuid4())[:8]}")
		jd_collection.add(
			documents=jd_chunks,
			metadatas=[{"source": job_description_url}] * len(jd_chunks),
			ids=[str(uuid.uuid4()) for _ in jd_chunks],
		)
	except Exception as e:
		logging.error(f"Error fetching or processing job description: {e}")
		raise ValueError(f"Failed to fetch job description: {e}")

	# Tools (same as strategic experience agent)
	def resume_query_tool(queries: list[str], top_k: int = 4) -> list[dict]:
		"""
		A tool for retrieving relevant information from a resume collection based on provided queries.
        Sample questions you may want to ask include:
          - "What are the candidate's key skills?"
          - "Can you provide examples of the candidate's work experience?"
          - "What education does the candidate have?"
          - "What are the responsibilities in the candidate's previous roles?"

		Args:
			queries (list[str]): A list of query strings (questions) to search for in the resume collection.
			top_k (int, optional): The maximum number of top results to return for each query. Defaults to 4.

		Returns:
			list[dict]: A list of dictionaries, each containing the retrieved document, its metadata, and the relevance score.

		This function queries the resume collection and returns the most relevant documents for the given queries, helping to extract targeted information from resumes.
		"""
		logging.info(f"Querying resume collection with queries: {queries}")
		results_out: list[dict] = []
		results = resume_collection.query(query_texts=queries, n_results=top_k)
		for doc, meta, score in zip(results.get('documents', []), results.get('metadatas', []), results.get('distances', [])):
			results_out.append({"document": doc, "metadata": meta, "score": score})
		return results_out

	def job_description_query_tool(queries: list[str], top_k: int = 10) -> list[dict]:
		"""
		A tool for querying and retrieving information about job descriptions.
        Sample questions you may want to ask include:
          - "What are the key responsibilities of the role?"
          - "What skills are required for the position?"
          - "What is the expected experience level for candidates?"
          - "What angle should the candidate take when approaching this role?"

		This function interacts with a job description collection to find relevant
		documents, metadata, and scores based on the provided queries. It is useful
		for extracting insights or details about job descriptions that match the
		given search criteria.

		Args:
			queries (list[str]): A list of query strings (questions) to search for in the job description collection.
			top_k (int, optional): The maximum number of results to retrieve. Defaults to 10.

		Returns:
			list[dict]: A list of dictionaries, each containing the following keys:
				- "document": The retrieved job description document.
				- "metadata": Metadata associated with the document.
				- "score": The relevance score of the document to the query.
		"""
		logging.info(f"Querying job description collection with queries: {queries}")
		results_out: list[dict] = []
		results = jd_collection.query(query_texts=queries, n_results=top_k)
		for doc, meta, score in zip(results.get('documents', []), results.get('metadatas', []), results.get('distances', [])):
			results_out.append({"document": doc, "metadata": meta, "score": score})
		return results_out

	# Single agent, no JSON/schema output
	try:
		experience_agent = LlmAgent(
			model="gemini-2.5-flash",
			name="experience_agent",
			description="Analyze resume + job description and extract relevant experience with creative insights.",
			instruction=(
	    "You are an elite Resume Strategist and Career Coach. Your mission is to create a "
	    "comprehensive STRATEGIC ACTION PLAN to guide the rewrite of a candidate's resume "
	    "experience section. You are not just rewriting bullets; you are providing the 'why' and "
	    "the 'how' behind the changes to perfectly align the resume with the target job."
	    "\n\n**Your process must follow these steps:**"
	    "\n1. **Analyze the Target:** Use the job_description_query_tool to deeply analyze the "
	    "Job Description. Identify the Top 5 Core Competencies (mixing hard skills like 'Python' "
	    "and soft skills like 'stakeholder management') and critical keywords."
	    "\n2. **Analyze the Source:** Use the resume_query_tool to analyze the user's Resume. "
	    "Identify all experiences, projects, skills and achievements that align with the target's "
	    "Core Competencies."
	    "\n3. **Create the Action Plan:** Synthesize your findings into a detailed plan with the "
	    "following specific sections using markdown formatting:"
	    "\n\n## Strategic Overview"
	    "\nStart with a brief, high-level summary of the core strategy. What is the main story "
	    "this resume needs to tell to be irresistible for this role?"
	    "\n\n## Key Themes & Keywords"
	    "\nList the most important keywords and themes from the job description that MUST be woven "
	    "into the experience bullets."
	    "\n\n## Bullet-by-Bullet Rewrite Plan"
	    "\nFor each relevant experience and skill in the resume, provide 2-3 specific, actionable recommendations for "
	    "rewriting the bullet points. For each recommendation, explicitly use the **STAR method** "
	    "(Situation, Task, Action, Result) as a guide. Emphasize **QUANTIFIABLE results** "
	    "(e.g., 'Increased efficiency by 20%', 'Managed a $50k budget', 'Reduced bug reports by 15%')."
	    "\n\n## Gap Analysis & Creative Insights"
	    "\nIdentify any gaps in experience or skills. Provide creative suggestions for how the candidate can reframe their existing experiences or highlight transferable skills to bridge these gaps. Suggest specific projects or accomplishments that could be emphasized to compensate for any missing direct experience."
	    "\n\n## Narrative Suggestions"
	    "\nProvide suggestions for how the candidate can effectively communicate their narrative throughout the resume. This includes tips on framing their experiences, highlighting key achievements, and ensuring a cohesive story that aligns with the job description. Speak in second person to your team (e.g., 'You should emphasize the clients leadership skills by...')"
	    "\n\n## Tone & Voice"
	    "\nYour tone should be professional, encouraging, and authoritative. You are an expert coach empowering the candidate to land their dream job. Frame your recommendations as strategic advice, not just edits."
	    "\n\nFinal Instruction: Produce a full implementation plan with detailed explanations and strategy to be followed by an LLM, formatted markdown document as your final answer. THIS DOCUMENT YOU ARE CREATING IS GUIDANCE FOR A TEAM TO CRAFT A RESUME AND COVER LETTER SO BE SURE TO WRITE IT WITH THAT AUDIENCE IN MIND."
			),
			planner=BuiltInPlanner(
				thinking_config=types.ThinkingConfig(
					include_thoughts=True,
					thinking_budget=4096,
				)
			),
			generate_content_config=types.GenerateContentConfig(temperature=1),
			tools=[resume_query_tool, job_description_query_tool],
		)

		# Session and runner setup (shared resources)
		session_service = InMemorySessionService()
		session_id = "test-session-123"
		user_id = "test-123"
		session = await session_service.create_session(user_id=user_id, session_id=session_id, app_name="experience_agent_only")
		runner = Runner(agent=experience_agent, session_service=session_service, app_name="experience_agent_only")
	  
		content_parts = [
			types.Part(text=(
				f"Perform a strategic analysis for resume {resume.id} against job url {job_description_url}. "
				f"Extract and analyze relevant experience, skills, projects, and create a compelling summary."
			))
		]

		final_text: str = ""
		async for event in runner.run_async(
			user_id=user_id,
			session_id=session_id,
			new_message=types.Content(role="user", parts=content_parts)
		):
			if hasattr(event, "is_final_response") and event.is_final_response():
				if getattr(event, "content", None) and getattr(event.content, "parts", None):
					part = event.content.parts[0]
					logging.info(f"Parts length: {len(event.content.parts)}")
	                
					if hasattr(part, "text") and part.text:
						final_text = part.text.strip()
		
		return final_text
	except Exception as e:
		logging.error(f"Error during agent execution: {e}")
		raise ValueError(f"Failed to execute experience agent: {e}")


__all__ = [
	"experience_agent_isolated",
]
