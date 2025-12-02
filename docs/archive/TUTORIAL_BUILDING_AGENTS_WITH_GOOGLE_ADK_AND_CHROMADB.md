# Building Production-Ready AI Agents with Google ADK and ChromaDB: A Deep Dive

## Introduction

In this comprehensive tutorial, we'll explore how to build sophisticated multi-agent systems using **Google's Agent Development Kit (ADK)** and **ChromaDB** for semantic search. We'll be walking through a real-world application called **RMCraft** - a FastAPI-based system that uses AI agents to generate, analyze, and optimize resumes and cover letters.

By the end of this tutorial, you'll understand:
- How to structure multi-agent workflows with Google ADK
- How to use ChromaDB for semantic search over structured data
- How to orchestrate complex agent interactions
- Best practices for production deployment

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Setting Up the Foundation](#setting-up-the-foundation)
3. [Understanding Google ADK Fundamentals](#understanding-google-adk-fundamentals)
4. [Integrating ChromaDB for Semantic Search](#integrating-chromadb-for-semantic-search)
5. [Building Multi-Agent Workflows](#building-multi-agent-workflows)
6. [Advanced Patterns: Theme Generation](#advanced-patterns-theme-generation)
7. [Production Considerations](#production-considerations)

---

## Architecture Overview

RMCraft is built on a modern Python stack:

```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115.0"
google-adk = "^1.12.0"
google-generativeai = "^0.8.5"
chromadb = "*"
beanie = "^2.0.0"        # MongoDB ODM
weasyprint = "^66.0"      # PDF generation
```

### High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FastAPI Layer                            │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────┐   │
│  │  /resumes  │  │   /themes    │  │  /cover-letters      │   │
│  └─────┬──────┘  └──────┬───────┘  └──────────┬───────────┘   │
└────────┼─────────────────┼───────────────────────┼──────────────┘
         │                 │                       │
         ▼                 ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Orchestrator Layer                            │
│  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Strategic Resume│  │    Theme     │  │  Cover Letter    │  │
│  │  Orchestrator   │  │  Generator   │  │  Orchestrator    │  │
│  └────────┬────────┘  └──────┬───────┘  └────────┬─────────┘  │
└───────────┼────────────────────┼──────────────────┼─────────────┘
            │                    │                  │
            ▼                    ▼                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Layer (Google ADK)                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  Sequential & Parallel Agent Workflows                    │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐               │  │
│  │  │ Analyst  │→│  Writer  │→│  Editor  │  (Sequential)   │  │
│  │  └──────────┘  └──────────┘  └──────────┘               │  │
│  │                                                            │  │
│  │  ┌──────────┐     ┌──────────┐                           │  │
│  │  │ Resume   │ ⇅   │  Cover   │           (Parallel)      │  │
│  │  │ Agent    │     │  Letter  │                           │  │
│  │  └──────────┘     └──────────┘                           │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────┬─────────────────────┬────────────────┬──────────┘
                │                     │                │
                ▼                     ▼                ▼
    ┌───────────────────┐ ┌───────────────────┐ ┌────────────────┐
    │   ChromaDB        │ │   MongoDB         │ │  External APIs │
    │ (Vector Search)   │ │  (via Beanie)     │ │  (Job Sites)   │
    └───────────────────┘ └───────────────────┘ └────────────────┘
```

### Project Structure

The application follows a clear separation of concerns:

```
app/
├── agents/              # ADK agent definitions
│   ├── resume/         # Resume-specific agents
│   ├── cover_letter/   # Cover letter agents
│   ├── theme_agents.py # Theme generation agents
│   └── triage/         # Theme debugging agents
├── features/           # Orchestrators
├── services/           # Business logic
├── api/v1/endpoints/   # FastAPI routes
└── tools/              # Custom ADK tools
```

This architecture demonstrates a key principle: **agents are the intelligence layer, while orchestrators coordinate workflows and services handle persistence**.

---

## Setting Up the Foundation

### Project Dependencies

First, let's understand the core dependencies:

```bash
poetry add fastapi uvicorn google-adk chromadb beanie pymongo
```

### Database Configuration with Beanie

RMCraft uses MongoDB with Beanie (an async ODM) for persistence:

```python
from beanie import Document, init_beanie
from pymongo import AsyncMongoClient
import inspect

async def connect_to_mongo():
    db.client = AsyncMongoClient(mongo_uri)
    
    # Auto-discover all Beanie Document models
    document_models = [
        obj for _, obj in inspect.getmembers(app.schemas, inspect.isclass)
        if issubclass(obj, Document) and obj is not Document
    ]
    
    await init_beanie(
        database=db.client[os.getenv("MONGODB_CLUSTER")],
        document_models=document_models
    )
```

**Key Insight**: Using `inspect.getmembers()` for auto-discovery means you don't need to manually register each model - just inherit from `Document` and you're done.

### FastAPI Lifecycle Management

Connect to databases during startup and cleanup on shutdown:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

app = FastAPI(title="RMCraft API", version="0.2.0", lifespan=lifespan)
```

---

## Understanding Google ADK Fundamentals

Google ADK provides a powerful framework for building agentic systems. Let's break down the core concepts with real examples from RMCraft.

### Core Components

1. **LlmAgent**: The basic building block
2. **SessionService**: Manages conversation state
3. **Runner**: Executes agent workflows
4. **Tools**: Extend agent capabilities

### Creating Your First Agent

Here's a simplified agent from the strategic resume analyzer:

```python
from google.adk.agents import LlmAgent
from google.adk.planners import BuiltInPlanner
from google.genai import types

experience_agent = LlmAgent(
    model="gemini-2.5-flash",
    name="experience_analyst",
    description="Analyzes work experience relevance to job descriptions",
    instruction=(
        "You are an expert resume analyst. Analyze the candidate's work "
        "experience and identify the most relevant accomplishments for "
        "the target job description."
    ),
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024
        )
    ),
    generate_content_config=types.GenerateContentConfig(
        temperature=0.7,
        response_mime_type="application/json",
        response_schema={
            "type": "object",
            "properties": {
                "relevant_experiences": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            }
        }
    )
)
```

**Key Points**:

- **ThinkingConfig**: Enables chain-of-thought reasoning (new in Gemini 2.0)
- **response_schema**: Enforces structured JSON output
- **thinking_budget**: Token allocation for reasoning (prevents runaway costs)

### Session Management: The Official Pattern

One of the most common mistakes with ADK is improper session management. Here's the **official pattern** verified against Google's documentation:

```
┌──────────────────────────────────────────────────────────────────┐
│                    ADK Session Flow                              │
│                                                                  │
│  1. Create Session Service                                      │
│     session_service = InMemorySessionService()                  │
│                          │                                       │
│                          ▼                                       │
│  2. Create Session (MUST AWAIT!)                                │
│     await session_service.create_session(...)                   │
│                          │                                       │
│                          ▼                                       │
│  3. Create Agent                                                │
│     agent = LlmAgent(...)                                       │
│                          │                                       │
│                          ▼                                       │
│  4. Create Runner (links agent + session service)               │
│     runner = Runner(agent, session_service, app_name)           │
│                          │                                       │
│                          ▼                                       │
│  5. Run Agent (async iteration)                                 │
│     async for event in runner.run_async(...):                   │
│         if event.is_final_response():                           │
│             return event.content                                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```python
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types
import uuid

async def run_agent_workflow():
    # Pattern 1: Create session service
    session_service = InMemorySessionService()
    
    # Pattern 2: Create session with await (CRITICAL!)
    session_id = uuid.uuid4().hex
    session = await session_service.create_session(
        app_name="resume_analyzer",
        user_id="user_123",
        session_id=session_id
    )
    
    # Pattern 3: Create runner with session service
    runner = Runner(
        agent=experience_agent,
        session_service=session_service,
        app_name="resume_analyzer"
    )
    
    # Pattern 4: Create content with proper structure
    content = types.Content(
        role='user',
        parts=[types.Part(text="Analyze this resume...")]
    )
    
    # Pattern 5: Async event processing
    async for event in runner.run_async(
        new_message=content,
        session_id=session_id,
        user_id="user_123"
    ):
        if event.is_final_response():
            return event.content.parts[0].text
```

**Common Mistakes to Avoid**:

❌ Forgetting `await` on `create_session()`
❌ Not passing `session_id` to `run_async()`
❌ Incorrect `role` parameter (must be `'user'`, not `'USER'`)

---

## Integrating ChromaDB for Semantic Search

ChromaDB is a vector database perfect for semantic search over your data. RMCraft uses it to enable agents to intelligently query resume and job description data.

### Why ChromaDB?

Traditional keyword search fails when matching resumes to job descriptions because:
- Synonyms aren't captured ("developed" vs "built" vs "created")
- Context matters ("led team" is different from "team member")
- Semantic similarity is more important than exact matches

```
┌──────────────────────────────────────────────────────────────────┐
│              ChromaDB Integration Architecture                   │
│                                                                  │
│  Resume JSON                    Job Description URL             │
│       │                                │                         │
│       ▼                                ▼                         │
│  ┌─────────────┐              ┌─────────────────┐              │
│  │  Transform  │              │  Fetch & Chunk  │              │
│  │  to Docs    │              │     Content     │              │
│  └──────┬──────┘              └────────┬────────┘              │
│         │                               │                       │
│         ▼                               ▼                       │
│  ┌─────────────────────────────────────────────┐              │
│  │         ChromaDB Collections                │              │
│  │  ┌────────────────┐  ┌─────────────────┐  │              │
│  │  │ Resume Docs    │  │   JD Chunks     │  │              │
│  │  │ • Experiences  │  │ • Requirements  │  │              │
│  │  │ • Projects     │  │ • Descriptions  │  │              │
│  │  │ • Skills       │  │ • Benefits      │  │              │
│  │  │ • Education    │  │                 │  │              │
│  │  └────────┬───────┘  └────────┬────────┘  │              │
│  └───────────┼──────────────────────┼─────────┘              │
│              │                      │                         │
│              ▼                      ▼                         │
│  ┌──────────────────────────────────────────┐                │
│  │      Query Tools (Agent Interface)       │                │
│  │  resume_query_tool(queries, top_k)       │                │
│  │  job_description_query_tool(queries, k)  │                │
│  └────────────────────┬─────────────────────┘                │
│                       │                                       │
│                       ▼                                       │
│  ┌────────────────────────────────────────────────┐          │
│  │         ADK Agent with Tools                   │          │
│  │  • Semantic search across resume               │          │
│  │  • Find relevant experience                    │          │
│  │  • Match skills to job requirements            │          │
│  └────────────────────────────────────────────────┘          │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### Data Preparation: Converting Resume to Documents

Here's the key function that transforms structured resume data into ChromaDB documents:

```python
import chromadb
import uuid

def process_resume_for_chroma(resume_json: dict) -> tuple[list[str], list[dict], list[str]]:
    """
    Convert a resume JSON object into documents, metadatas and ids for ChromaDB.
    Returns: (documents, metadatas, ids)
    """
    documents: list[str] = []
    metadatas: list[dict] = []
    ids: list[str] = []

    # Strategy 1: Each responsibility becomes a separate document
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

    # Strategy 2: Project descriptions
    for project in resume_json.get("projects", []):
        name = project.get("name", "") or ""
        desc = project.get("description", "") or ""
        doc_content = f"{name}: {desc}".strip(": ").strip()
        if not doc_content:
            continue
        documents.append(doc_content)
        metadatas.append({
            "type": "project",
            "name": project.get("name") or "Unknown Project"
        })
        ids.append(project.get("id") or str(uuid.uuid4()))

    # Strategy 3: Aggregate skills into a single summary
    skill_list = [s.get("name") for s in resume_json.get("skills", []) if s.get("name")]
    if skill_list:
        documents.append("Key technical skills include: " + ", ".join(skill_list))
        metadatas.append({"type": "skills_summary"})
        ids.append("skills_summary_01")

    # Strategy 4: Professional summary
    if resume_json.get("summary"):
        documents.append(resume_json["summary"])
        metadatas.append({"type": "summary"})
        ids.append("main_summary_01")

    return documents, metadatas, ids
```

**Design Decisions**:

1. **Granular vs. Aggregate**: Experience items are granular (one doc per responsibility) while skills are aggregated. This is because:
   - Responsibilities benefit from semantic matching at the bullet-point level
   - Skills work better as a cohesive list for context

2. **Metadata Structure**: Each metadata includes `type` for filtering and context-specific fields. This enables queries like "show me all experiences at tech companies".

3. **ID Strategy**: Use UUIDs for unique items, fixed IDs for singletons (like "skills_summary_01").

### Setting Up ChromaDB Collections

```python
async def cover_letter_orchestrator(resume_id: str, job_description_url: str):
    # Initialize ChromaDB (ephemeral for per-request isolation)
    chroma_client = chromadb.EphemeralClient()
    
    # Create collection for resume data
    resume_collection = chroma_client.get_or_create_collection(
        name="cover_letter_resume"
    )
    
    # Fetch and process resume
    resume = await ResumeResponse.find_one({"_id": ObjectId(resume_id)})
    documents, metadatas, ids = process_resume_for_chroma(resume.model_dump())
    
    # Add to collection (ChromaDB handles embedding automatically)
    resume_collection.add(
        documents=documents,
        metadatas=metadatas,
        ids=ids
    )
    
    # Create separate collection for job description
    jd_collection = chroma_client.get_or_create_collection(
        name=f"cover_letter_jd_{str(uuid.uuid4())[:8]}"
    )
    
    # Fetch job description from URL
    job_description_chunks = await get_url_contents(job_description_url)
    jd_collection.add(
        documents=job_description_chunks,
        metadatas=[{"source": job_description_url}] * len(job_description_chunks),
        ids=[str(uuid.uuid4()) for _ in job_description_chunks],
    )
```

**Why EphemeralClient?**

Using `EphemeralClient()` creates an in-memory database that's discarded after the request. This is perfect for:
- Stateless API endpoints
- Per-request data isolation
- No cleanup required

For production with persistent data, use `PersistentClient(path="./chroma_db")`.

### Creating Query Tools for Agents

ADK agents can't directly access ChromaDB - they need **tools**. Here's how to create query tools:

```python
def create_resume_query_tool(resume_collection):
    """Factory function to create a resume query tool with collection closure."""
    
    def resume_query_tool(queries: list[str], top_k: int = 4) -> list[dict]:
        """Query resume collection for relevant information."""
        resume_parts = []
        results = resume_collection.query(
            query_texts=queries,
            n_results=top_k
        )
        
        for doc, meta, score in zip(
            results.get('documents', []),
            results.get('metadatas', []),
            results.get('distances', [])
        ):
            resume_parts.append({
                "document": doc,
                "metadata": meta,
                "score": score
            })
        
        return resume_parts
    
    return resume_query_tool
```

**Key Pattern**: The factory function creates a closure over `resume_collection`, so the agent's tool has access to the specific collection instance.

### Passing Tools to Agents

```python
from app.agents.cover_letter.analyst_agent import create_cover_letter_analyst_agent

# Create query tools
resume_query = create_resume_query_tool(resume_collection)
jd_query = create_jd_query_tool(jd_collection)

# Create agent with tools
analyst_agent = create_cover_letter_analyst_agent(
    resume_query_tool=resume_query,
    job_description_query_tool=jd_query
)
```

Inside the agent creation function:

```python
def create_cover_letter_analyst_agent(resume_query_tool, job_description_query_tool):
    return LlmAgent(
        model="gemini-2.5-flash",
        name="cover_letter_analyst",
        description="Analyzes resume and job description to identify key points",
        instruction=(
            "You have access to two tools:\n"
            "1. resume_query_tool(queries: list[str], top_k: int) - Query resume\n"
            "2. job_description_query_tool(queries: list[str], top_k: int) - Query JD\n\n"
            "Use these tools to find relevant information before responding."
        ),
        # Tools are passed as a list
        tools=[
            FunctionTool(func=resume_query_tool),
            FunctionTool(func=job_description_query_tool)
        ]
    )
```

---

## Building Multi-Agent Workflows

The real power of ADK emerges when you orchestrate multiple agents. Let's explore different patterns.

### Pattern 1: Sequential Agent Workflow

Sequential workflows execute agents one after another, passing context between them:

```python
from google.adk.agents import SequentialAgent

# Define individual agents
analyst_agent = create_cover_letter_analyst_agent(resume_query, jd_query)
writer_agent = create_cover_letter_writer_agent(resume_query, jd_query)
editor_agent = create_cover_letter_editor_agent()

# Compose into sequential workflow
cover_letter_workflow = SequentialAgent(
    name="cover_letter_workflow",
    description="Analyzes, writes, and edits a cover letter",
    sub_agents=[
        analyst_agent,  # Step 1: Analyze
        writer_agent,   # Step 2: Write draft
        editor_agent    # Step 3: Polish
    ]
)
```

**Visual Flow**:

```
┌─────────────────────────────────────────────────────────────────┐
│              Sequential Agent Workflow                          │
│                                                                 │
│  User Input                                                     │
│      │                                                          │
│      ▼                                                          │
│  ┌──────────────────────┐                                      │
│  │  Analyst Agent       │                                      │
│  │  • Queries resume DB │                                      │
│  │  • Queries JD DB     │                                      │
│  │  • Identifies themes │                                      │
│  └──────────┬───────────┘                                      │
│             │                                                   │
│             │ Context: Analysis Results                        │
│             │ (via session state)                              │
│             ▼                                                   │
│  ┌──────────────────────┐                                      │
│  │  Writer Agent        │                                      │
│  │  • Reads analysis    │                                      │
│  │  • Queries examples  │                                      │
│  │  • Writes draft      │                                      │
│  └──────────┬───────────┘                                      │
│             │                                                   │
│             │ Context: Draft + Analysis                        │
│             │ (via session state)                              │
│             ▼                                                   │
│  ┌──────────────────────┐                                      │
│  │  Editor Agent        │                                      │
│  │  • Reads draft       │                                      │
│  │  • Polishes language │                                      │
│  │  • Fixes errors      │                                      │
│  └──────────┬───────────┘                                      │
│             │                                                   │
│             ▼                                                   │
│  Final Cover Letter                                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**How it works**:
1. Analyst agent receives user input, queries ChromaDB, produces analysis
2. Writer agent receives analysis context, queries ChromaDB, produces draft
3. Editor agent receives draft, produces final polished version

**Context Flow**: Each agent has access to the full conversation history via the session.

### Pattern 2: Parallel Agent Workflow

Parallel workflows execute agents concurrently for performance:

```python
from google.adk.agents import ParallelAgent

# Create parallel workflow for theme generation
parallel_theme_creation = ParallelAgent(
    name="parallel_theme_creation",
    description="Generates resume and cover letter themes concurrently",
    sub_agents=[
        resume_theme_agent,       # Runs in parallel
        cover_letter_theme_agent  # Runs in parallel
    ]
)
```

**Visual Flow**:

```
┌─────────────────────────────────────────────────────────────────┐
│              Parallel Agent Workflow                            │
│                                                                 │
│  Design Brief (shared input)                                   │
│            │                                                    │
│            ├─────────────────┬──────────────────┐              │
│            │                 │                  │              │
│            ▼                 ▼                  ▼              │
│  ┌──────────────────┐  ┌──────────────────┐                  │
│  │ Resume Theme     │  │ Cover Letter     │                  │
│  │ Agent            │  │ Theme Agent      │  (Run Concurrently)│
│  │                  │  │                  │                  │
│  │ • Analyzes brief │  │ • Analyzes brief │                  │
│  │ • Creates Jinja2 │  │ • Creates Jinja2 │                  │
│  │ • Generates CSS  │  │ • Generates CSS  │                  │
│  └────────┬─────────┘  └────────┬─────────┘                  │
│           │                     │                             │
│           └──────────┬──────────┘                             │
│                      │                                         │
│                      ▼                                         │
│           Both results combined                               │
│           (no blocking between agents)                        │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

**When to use parallel**:
- Agents are independent (don't need each other's outputs)
- Performance is critical
- Operations can be done simultaneously (e.g., generating two separate templates)

### Pattern 3: Hybrid Workflows

Combine sequential and parallel for complex orchestration:

```python
# Step 1: Analyze design request (sequential - must go first)
theme_analyst_agent = LlmAgent(...)

# Step 2: Generate themes in parallel (independent tasks)
parallel_theme_creation = ParallelAgent(
    name="parallel_theme_creation",
    sub_agents=[resume_theme_agent, cover_letter_theme_agent]
)

# Step 3: Combine into full workflow
full_theme_workflow = SequentialAgent(
    name="full_theme_workflow",
    description="Analyzes design request and generates complete theme package",
    sub_agents=[
        theme_analyst_agent,      # Must complete first
        parallel_theme_creation   # Then run these in parallel
    ]
)
```

This creates a directed acyclic graph (DAG):

```
┌─────────────────────────────────────────────────────────────────┐
│              Hybrid Sequential + Parallel Workflow              │
│                                                                 │
│  User Input (text + image)                                     │
│            │                                                    │
│            ▼                                                    │
│  ┌──────────────────────┐                                      │
│  │ Theme Analyst Agent  │  ◄── SEQUENTIAL: Must complete first │
│  │ • Analyzes prompt    │                                      │
│  │ • Analyzes image     │                                      │
│  │ • Creates brief      │                                      │
│  └──────────┬───────────┘                                      │
│             │                                                   │
│             │ Context: Design Brief                            │
│             │                                                   │
│             ├─────────────────┬──────────────────┐             │
│             │                 │                  │             │
│             ▼                 ▼                  ▼             │
│  ┌────────────────────┐  ┌────────────────────┐              │
│  │ Resume Theme       │  │ Cover Letter       │              │
│  │ Agent              │  │ Theme Agent        │ ◄── PARALLEL  │
│  │                    │  │                    │     (Independent)│
│  │ • Reads brief      │  │ • Reads brief      │              │
│  │ • Creates template │  │ • Creates template │              │
│  │ • Generates CSS    │  │ • Generates CSS    │              │
│  └─────────┬──────────┘  └─────────┬──────────┘              │
│            │                        │                          │
│            └───────────┬────────────┘                          │
│                        │                                       │
│                        ▼                                       │
│             Combined Theme Package                            │
│                                                                │
└─────────────────────────────────────────────────────────────────┘
```

### Complete Orchestrator Example

Here's a simplified but complete orchestrator from RMCraft:

```python
async def cover_letter_orchestrator(
    resume_id: str,
    job_description_url: str,
    optional_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """
    Main orchestrator for strategic cover letter generation.
    """
    
    # Step 1: Setup ChromaDB
    chroma_client = chromadb.EphemeralClient()
    resume_collection = chroma_client.get_or_create_collection(name="resume")
    jd_collection = chroma_client.get_or_create_collection(name="jd")
    
    # Step 2: Load and process data
    resume = await ResumeResponse.find_one({"_id": ObjectId(resume_id)})
    documents, metadatas, ids = process_resume_for_chroma(resume.model_dump())
    resume_collection.add(documents=documents, metadatas=metadatas, ids=ids)
    
    job_description_chunks = await get_url_contents(job_description_url)
    jd_collection.add(
        documents=job_description_chunks,
        metadatas=[{"source": job_description_url}] * len(job_description_chunks),
        ids=[str(uuid.uuid4()) for _ in job_description_chunks]
    )
    
    # Step 3: Create query tools
    resume_query = lambda queries, top_k=4: resume_collection.query(
        query_texts=queries, n_results=top_k
    )
    jd_query = lambda queries, top_k=10: jd_collection.query(
        query_texts=queries, n_results=top_k
    )
    
    # Step 4: Build workflow
    analyst_agent = create_cover_letter_analyst_agent(resume_query, jd_query)
    writer_agent = create_cover_letter_writer_agent(resume_query, jd_query)
    editor_agent = create_cover_letter_editor_agent()
    
    workflow = SequentialAgent(
        name="cover_letter_workflow",
        description="Complete cover letter generation pipeline",
        sub_agents=[analyst_agent, writer_agent, editor_agent]
    )
    
    # Step 5: Execute workflow
    session_service = InMemorySessionService()
    session_id = uuid.uuid4().hex
    await session_service.create_session(
        app_name="cover_letter",
        user_id="user_123",
        session_id=session_id
    )
    
    runner = Runner(
        agent=workflow,
        session_service=session_service,
        app_name="cover_letter"
    )
    
    content = types.Content(
        role='user',
        parts=[types.Part(text=f"Job Description URL: {job_description_url}")]
    )
    
    # Step 6: Process results
    final_result = {}
    async for event in runner.run_async(
        new_message=content,
        session_id=session_id,
        user_id="user_123"
    ):
        if event.is_final_response():
            final_result = json.loads(event.content.parts[0].text)
    
    return final_result
```

---

## Advanced Patterns: Theme Generation

Let's explore a sophisticated real-world use case: multimodal theme generation with parallel agents.

### The Challenge

RMCraft needs to generate matching resume and cover letter themes based on:
- A text prompt describing the desired style
- An inspiration image showing visual preferences

This requires:
1. Analyzing the design request (text + image)
2. Creating detailed design specifications
3. Generating Jinja2 templates in parallel
4. Generating corresponding CSS stylesheets
5. Validating and saving to database

```
┌──────────────────────────────────────────────────────────────────┐
│           Theme Generation: End-to-End Flow                      │
│                                                                  │
│  1. API Request                                                 │
│     POST /themes/create                                         │
│     • design_prompt (text)                                      │
│     • inspiration_image (file)                                  │
│            │                                                     │
│            ▼                                                     │
│  2. Orchestrator                                                │
│     ┌────────────────────────────────────┐                     │
│     │ create_and_save_theme()            │                     │
│     │ • Setup ADK session                │                     │
│     │ • Create multimodal input          │                     │
│     │ • Execute agent workflow           │                     │
│     └─────────────┬──────────────────────┘                     │
│                   │                                             │
│                   ▼                                             │
│  3. Agent Workflow (Sequential + Parallel)                     │
│     ┌────────────────────────────────┐                         │
│     │ Theme Analyst Agent            │                         │
│     │ Input: Text + Image            │                         │
│     │ Output: Design Brief (JSON)    │                         │
│     └─────────────┬──────────────────┘                         │
│                   │                                             │
│              ┌────┴────┐                                        │
│              ▼         ▼                                        │
│     ┌──────────────┐ ┌──────────────┐                         │
│     │ Resume Agent │ │ CoverLetter  │  (Parallel execution)   │
│     │              │ │ Agent        │                         │
│     │ Output:      │ │ Output:      │                         │
│     │ • template   │ │ • template   │                         │
│     │ • styles     │ │ • styles     │                         │
│     └──────┬───────┘ └──────┬───────┘                         │
│            │                │                                   │
│            └────────┬───────┘                                   │
│                     │                                           │
│                     ▼                                           │
│  4. Database Persistence                                       │
│     ┌────────────────────────────────┐                         │
│     │ save_theme_from_agents()       │                         │
│     │ • Validate against schemas     │                         │
│     │ • Create ThemeDoc (resume)     │                         │
│     │ • Create ThemeDoc (cover)      │                         │
│     │ • Create ThemePackageDoc       │                         │
│     │ • Save to MongoDB via Beanie   │                         │
│     └─────────────┬──────────────────┘                         │
│                   │                                             │
│                   ▼                                             │
│  5. API Response                                               │
│     { id, name, description, ... }                             │
│                                                                 │
└──────────────────────────────────────────────────────────────────┘
```

### Agent Architecture

```python
# Agent 1: Creative Director (analyzes design request)
theme_analyst_agent = LlmAgent(
    model="gemini-2.5-pro",  # Pro model for visual analysis
    name="theme_analyst_agent",
    description="Analyzes prompt and image to produce design brief",
    instruction=(
        "You are an expert Creative Director. Analyze the text prompt "
        "and inspiration image to create a comprehensive design blueprint. "
        "Output a detailed Markdown document with:\n"
        "- Theme Name and Description\n"
        "- Color Palette (with hex codes)\n"
        "- Typography (Google Fonts)\n"
        "- Design Direction for Resume Agent\n"
        "- Design Direction for Cover Letter Agent"
    ),
    output_key="creative_director_brief"
)

# Agent 2A: Resume Template Developer
resume_theme_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="resume_theme_agent",
    description="Generates Jinja2 template + CSS for resume",
    instruction=(
        "You are a UI developer specializing in print design. "
        "Using the creative director's brief, generate:\n"
        "1. A Jinja2 template using ResumeResponse schema field names\n"
        "2. Print-optimized CSS with proper page breaks\n\n"
        "CRITICAL SPECIFICATIONS:\n"
        "- Use pt for font-size, in for margins\n"
        "- Design for Letter/A4 paper size\n"
        "- Use page-break-inside: avoid for sections\n"
        "- Include utility classes for layout control\n"
        "- Follow the creative brief's color palette exactly"
    ),
    output_schema=ThemeGenerationOutputSchema,
    output_key="resume_theme"
)

# Agent 2B: Cover Letter Template Developer
cover_letter_theme_agent = LlmAgent(
    model="gemini-2.5-pro",
    name="cover_letter_theme_agent",
    description="Generates Jinja2 template + CSS for cover letter",
    instruction=(
        "You are a UI developer specializing in print design. "
        "Using the creative director's brief, generate a cover letter "
        "template that visually complements the resume design."
    ),
    output_schema=ThemeGenerationOutputSchema,
    output_key="cover_letter_theme"
)
```

### Multimodal Input Handling

One powerful feature of Gemini models is multimodal support. Here's how to pass images to agents:

```python
from google.genai import types

async def create_and_save_theme(
    design_prompt: str,
    image_data: bytes,
    image_mime_type: str,
    user_id: str
):
    # Build workflow (sequential + parallel hybrid)
    parallel_theme_creation = ParallelAgent(
        name="parallel_theme_creation",
        sub_agents=[resume_theme_agent, cover_letter_theme_agent]
    )
    
    full_theme_workflow = SequentialAgent(
        name="full_theme_workflow",
        sub_agents=[theme_analyst_agent, parallel_theme_creation]
    )
    
    # Setup runner
    session_service = InMemorySessionService()
    session_id = uuid.uuid4().hex
    await session_service.create_session(
        session_id=session_id,
        app_name="theme_generator",
        user_id=user_id
    )
    
    runner = Runner(
        agent=full_theme_workflow,
        session_service=session_service,
        app_name="theme_generator"
    )
    
    # Create multimodal content (TEXT + IMAGE)
    content = types.Content(
        role='user',
        parts=[
            types.Part(text=design_prompt),
            types.Part(
                inline_data=types.Blob(
                    mime_type=image_mime_type,
                    data=image_data
                )
            )
        ]
    )
    
    # Execute and collect results
    final_response = {}
    async for event in runner.run_async(
        new_message=content,
        session_id=session_id,
        user_id=user_id
    ):
        if event.is_final_response() and event.content:
            response_text = event.content.parts[0].text
            try:
                response_data = json.loads(response_text)
                
                # Map agent output keys to results
                if event.author == "theme_analyst_agent":
                    final_response["theme_brief"] = response_data
                elif event.author == "resume_theme_agent":
                    final_response["resume_theme"] = response_data
                elif event.author == "cover_letter_theme_agent":
                    final_response["cover_letter_theme"] = response_data
                    
            except json.JSONDecodeError:
                logger.error(f"Failed to parse JSON from {event.author}")
    
    return final_response
```

**Key Multimodal Patterns**:

1. **Inline Data**: Use `types.Blob()` for images
2. **MIME Types**: Specify correct type (e.g., "image/png", "image/jpeg")
3. **Part Order**: Text first, then image works best
4. **Model Selection**: Use Pro models for complex visual analysis

**Multimodal Content Structure**:

```
┌──────────────────────────────────────────────────────────────────┐
│                  Multimodal Input Construction                   │
│                                                                  │
│  types.Content                                                  │
│  ├─ role: 'user'                                                │
│  └─ parts: [                                                    │
│       ├─ Part 1: Text                                           │
│       │  └─ types.Part(text="Create a modern theme...")         │
│       │                                                          │
│       └─ Part 2: Image                                          │
│          └─ types.Part(                                         │
│                inline_data=types.Blob(                          │
│                   mime_type="image/png",                        │
│                   data=<bytes>                                  │
│                )                                                 │
│             )                                                    │
│     ]                                                            │
│                                                                  │
│  Result: Agent receives both text and visual context            │
│          for more informed design decisions                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### Structured Output with Pydantic

ADK supports enforcing output schemas using Pydantic:

```python
from pydantic import BaseModel, Field

class ThemeGenerationOutputSchema(BaseModel):
    """Structured output for theme generation."""
    template: str = Field(
        description="Complete Jinja2 template string"
    )
    styles: str = Field(
        description="Complete CSS stylesheet"
    )

# Use in agent definition
resume_theme_agent = LlmAgent(
    ...,
    output_schema=ThemeGenerationOutputSchema,
    generate_content_config=types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=ThemeGenerationOutputSchema.model_json_schema()
    )
)
```

This ensures the agent always returns valid JSON matching your schema.

---

## Production Considerations

### Testing Strategy: Mock ADK

For unit tests and CI/CD, RMCraft implements a complete mock of Google ADK:

```
┌──────────────────────────────────────────────────────────────────┐
│              Development & Testing Strategy                      │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Production Environment                                     │ │
│  │  USE_MOCK_ADK=false                                         │ │
│  │                                                             │ │
│  │  from google.adk.agents import LlmAgent                    │ │
│  │  from google.adk.runners import Runner                     │ │
│  │  ↓                                                          │ │
│  │  Real Google ADK                                           │ │
│  │  • Actual API calls                                        │ │
│  │  • Real costs                                              │ │
│  │  • Network latency                                         │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  Test/Development Environment                              │ │
│  │  USE_MOCK_ADK=true                                         │ │
│  │                                                             │ │
│  │  from google.adk.agents import LlmAgent  ← Mocked!         │ │
│  │  from google.adk.runners import Runner   ← Mocked!         │ │
│  │  ↓                                                          │ │
│  │  Mock ADK (mock_adk.py)                                    │ │
│  │  • Predefined responses                                    │ │
│  │  • No API costs                                            │ │
│  │  • Instant execution                                       │ │
│  │  • Deterministic results                                   │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  Benefits:                                                      │
│  ✓ Fast CI/CD pipelines                                        │
│  ✓ No API keys needed in test environment                      │
│  ✓ Reproducible test results                                   │
│  ✓ Easy debugging with predictable outputs                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

```python
# mock_adk.py
class MockLlmAgent:
    def __init__(self, model, name, description, instruction, **kwargs):
        self.model = model
        self.name = name
        self.instruction = instruction
        self.output_key = kwargs.get('output_key')
    
    async def run_async(self, content, session_id, user_id):
        """Mock implementation with predefined responses"""
        # Return realistic test data
        yield MockEvent(
            author=self.name,
            content=MockContent(...),
            is_final=True
        )

# Usage in tests
os.environ['USE_MOCK_ADK'] = 'true'
from app.agents.resume.strategic_resume_agent import strategic_resume_agent

# Now uses mock automatically
result = await strategic_resume_agent(resume_id="test_123", job_description_url="...")
```

**Benefits**:
- No API costs during testing
- Deterministic responses
- Fast test execution
- CI/CD friendly

### Error Handling and Validation

Always validate agent outputs:

```python
async def process_agent_response(event):
    if not event.content or not event.content.parts:
        raise ValueError("Empty response from agent")
    
    response_text = event.content.parts[0].text
    
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from {event.author}: {e}")
        # Retry logic or fallback
        raise
    
    # Validate against schema
    try:
        validated = ThemeGenerationOutputSchema(**data)
    except ValidationError as e:
        logger.error(f"Schema validation failed: {e}")
        raise
    
    return validated
```

### Rate Limiting and Cost Control

```python
from google.adk.planners import BuiltInPlanner
from google.genai import types

# Set thinking budget to control token usage
agent = LlmAgent(
    ...,
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            include_thoughts=True,
            thinking_budget=1024  # Max tokens for reasoning
        )
    )
)
```

### Monitoring and Observability

```python
import logging

logger = logging.getLogger(__name__)

async for event in runner.run_async(...):
    # Log all events for debugging
    logger.info(f"Event: {type(event).__name__}, Author: {event.author}")
    
    if hasattr(event, 'content'):
        content_preview = str(event.content)[:200]
        logger.debug(f"Content preview: {content_preview}")
    
    if event.is_final_response():
        logger.info(f"Final response from {event.author}")
```

### Environment Configuration

Use Pydantic Settings for configuration:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str
    GOOGLE_API_KEY: str
    MONGODB_CLUSTER: str
    USE_MOCK_ADK: str = "false"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

settings = Settings()
```

### Database Patterns with Beanie

```python
from beanie import Document, Indexed
from pydantic import Field

class ThemeDoc(Document):
    """Beanie document for theme storage"""
    name: str = Field(...)
    description: str = Field(...)
    template: str = Field(...)
    styles: str = Field(...)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user_id: Indexed(str)  # Automatic index
    
    class Settings:
        name = "themes"  # MongoDB collection name

# Usage
async def save_theme(theme_data: dict) -> ThemeDoc:
    theme = ThemeDoc(**theme_data)
    await theme.insert()
    return theme

# Query
themes = await ThemeDoc.find(ThemeDoc.user_id == "user_123").to_list()
```

---

## Key Takeaways

### Google ADK Best Practices

1. **Always await session creation**: `await session_service.create_session(...)`
2. **Use SequentialAgent for dependent tasks**, ParallelAgent for independent tasks
3. **Implement ThinkingConfig** for complex reasoning tasks
4. **Enforce structured output** with Pydantic schemas
5. **Pass tools as closures** to avoid serialization issues

### ChromaDB Best Practices

1. **Granularity matters**: Break text into semantic units
2. **Use EphemeralClient** for stateless operations
3. **Add rich metadata** for filtering and context
4. **Query with multiple query texts** for better results
5. **Store document type in metadata** for filtering

### Architecture Best Practices

1. **Separate concerns**: Agents (intelligence), Orchestrators (workflow), Services (persistence)
2. **Use Beanie for MongoDB**: Type-safe ODM with async support
3. **Implement mock layers**: Essential for testing and development
4. **Log everything**: Agent events, ChromaDB queries, API calls
5. **Validate agent outputs**: Never trust unvalidated LLM responses

---

## Conclusion

Building production-ready AI agent systems requires understanding not just the tools, but how to architect them together effectively. Google ADK provides the orchestration layer, ChromaDB adds semantic search capabilities, and careful design patterns tie it all together.

The RMCraft project demonstrates that with the right architecture, you can build sophisticated multi-agent systems that:
- Generate complex artifacts (Jinja templates, CSS)
- Perform semantic analysis (resume matching)
- Handle multimodal inputs (text + images)
- Scale to production workloads

The patterns shown here - from session management to ChromaDB integration to multi-agent workflows - are applicable to any AI agent system you build.

### Next Steps

1. **Explore the full codebase**: The patterns shown here are simplified; the actual implementation has additional error handling, retry logic, and optimizations
2. **Experiment with different models**: Try Gemini 2.0 Flash, Pro, or even other providers via LiteLLM
3. **Build your own agents**: Start with a simple sequential workflow and gradually add complexity
4. **Join the community**: Google ADK is rapidly evolving - stay updated with official documentation

---

## Additional Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/)
- [Beanie ODM Documentation](https://beanie-odm.dev/)

**Repository**: This tutorial is based on the real-world RMCraft project, a production FastAPI application using Google ADK and ChromaDB.

---

*Tutorial written based on production code from RMCraft. All patterns shown are battle-tested in real-world usage.*
