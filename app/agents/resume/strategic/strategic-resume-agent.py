from google.adk.agents import Agent
from google.adk.tools import google_search
import chromadb


async def strategic_resume_agent(resume_id: str, job_description_url: str):
    # Initialize ChromaDB client
    chroma_client = chromadb.Client()

    collection = chroma_client.get_or_create_collection(name="resume_parts")

    # Step 0 - Get resume parts (Summary, Experience, Skills, Projects, Education) and store them in ChromaDB

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

    # Step 0 - Get resume parts (Summary, Experience, Skills, Projects, Education) and store them in ChromaDB

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