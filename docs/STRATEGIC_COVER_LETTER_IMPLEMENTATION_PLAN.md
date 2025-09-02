# Strategic Cover Letter Agent – Implementation Plan

Purpose: Define an agentic workflow (end-to-end) that generates a personalized, strategic cover letter using the same tools and patterns as Strategic Resume Analysis. This document is a complete LLM-executable plan: it specifies contracts, steps, prompts, files to touch, tests, and acceptance criteria so an LLM can implement the feature without further context.

## Goals
- Given inputs (resumeId, jobDescriptionUrl, optionalPrompt), produce a high-quality strategic cover letter tailored to the job.
- Reuse the same toolchain used by Strategic Resume Analysis:
  - Resume data retrieval + normalization + Chroma vector store access for retrieval.
  - Job description acquisition + normalization (URL-based fetch/parse).
- Keep API contracts stable and predictable; prefer additive changes.

## Inputs / Outputs (Contracts)
Inputs
- resumeId (string, required): existing resume in DB.
- jobDescriptionUrl (string, required): URL to scrape/parse.
- prompt (string, optional): user-provided direction (tone, highlights, priorities).

Primary Output (response model)
- status (int): 201 on success (if persisted) or 200 when returning draft only.
- message (string)
- data.coverLetter (object):
  - title (string) – optional, e.g., "Strategic Cover Letter"
  - jobDetails (JobProfileDetails-like object) – normalized from JD
  - openingParagraph (string)
  - bodyParagraphs (array of strings)
  - companyConnection (string | optional)
  - closingParagraph (string)
  - tone (enum: professional | creative | enthusiastic | formal) – optional
  - finalContent (string) – fully assembled HTML or Markdown string
  - resumeId (string)
  - jobProfileId (string | optional) – if job profiles are persisted
  - createdAt, updatedAt (timestamps) – if persisted

Secondary Outputs (for observability / optional persistence)
- artifacts: structured planning notes or outline used by the writer/editor agents.
- debug/logs: retrieval snippets from Chroma and key JD highlights.

Notes
- Prefer consistent casing with existing Pydantic types in `app/schemas/ResumeSchemas.py` where feasible (e.g., JobProfileDetails).

## Dependencies & Truth Sources
- Resume retrieval and normalization service(s) used by Strategic Resume Analysis.
- Chroma vector DB embedding/index for resumes (same collections, same schema).
- Job description fetch/parse tool used by Strategic Resume Analysis (URL → normalized details).
- Existing Pydantic models under `app/schemas/ResumeSchemas.py` (JobProfileDetails, etc.).
- FastAPI app patterns and testing conventions under `tests/` (strategic_* tests).

## Data Contracts (LLM-facing)
- Resume shape (normalized): name, summary, experiences, skills, projects, contact info. Treat fields as possibly partial and robustly handle missing data.
- Job description shape (normalized): title, company, description, requirements, responsibilities, skills, location, salary, source, url, createdAt.
- Cover letter content contract (LLM internal):
  - Outline: hook, role alignment, skill evidence (2–3 bullets), culture/mission tie-in, closing CTA.
  - Final rendering: clean HTML with minimal CSS or plain Markdown; avoid external images; ensure accessibility and ATS-friendly text.

## High-Level Architecture
- Orchestrator: `cover_letter_orchestrator` (new) – coordinates tools and sub-agents.
- Tools:
  - Resume Retriever + Chroma Retriever
  - Job Description Fetcher/Parser
- Agents:
  - cover_letter_analyst_agent – synthesizes JD + resume insights; produces outline + key talking points.
  - cover_letter_writer_agent – drafts opening, body, closing based on outline.
  - cover_letter_editor_agent – enforces tone/style, checks length, clarity, and ATS compliance.
- Assembler:
  - cover_letter_assembler – builds `finalContent` and structured fields.
- Persistence (optional but recommended): save a CoverLetter record or attach to the resume’s artifacts. If a dedicated table doesn’t exist, return the generated result without DB write, or store in a generic artifacts table where available.

## Detailed Workflow
1) Input validation
   - Validate `resumeId` exists; error 404 if not.
   - Validate `jobDescriptionUrl` is a URL; attempt fetch; if 4xx/5xx from source, return 502/503 accordingly.
   - Optional `prompt` can bias tone, role focus, or highlights.

2) Resume context
   - Load resume by `resumeId` via CRUD.
   - Normalize shape (same utilities as Strategic Resume Analysis).
   - Retrieve top-K relevant snippets from Chroma (skills, experiences, projects) using queries derived from JD title/keywords.

3) Job description context
   - Fetch and parse JD via existing tool; normalize to JobProfileDetails-like object.
   - Extract keywords, responsibilities, and role-critical criteria.

4) Analysis
   - cover_letter_analyst_agent merges JD and resume signals and returns:
     - Target role and company summary
     - 3–5 strongest matches (skills/experiences) with brief evidence
     - Optional company connection angle (mission, values, product)
     - Risks/gaps and mitigation suggestions
     - Outline (opening → body paragraphs → closing)

5) Drafting
   - cover_letter_writer_agent produces:
     - openingParagraph (hook + fit statement)
     - bodyParagraphs (2–3 paragraphs focusing on evidence and outcomes)
     - closingParagraph (clear CTA, gratitude)
     - optional companyConnection sentence
     - tone proposal; incorporate optional user prompt for direction

6) Editing & QA
   - cover_letter_editor_agent ensures:
     - Tone, length (e.g., 250–450 words), clarity, and ATS-friendly formatting
     - No hallucinated company names/dates; grounded to resume/JD
     - Friendly yet professional; avoids generic fluff

7) Assembly
   - cover_letter_assembler combines fields into finalContent (HTML or Markdown) and produces the structured payload with metadata.

8) Persistence (optional; if supported)
   - Save generated cover letter linked to `resumeId` (and optional `jobProfileId`).
   - Record createdAt/updatedAt; store inputs (resumeId, jobDescriptionUrl, prompt) for provenance.

9) Response
   - Return envelope with `data.coverLetter` containing both structured fields and `finalContent`.

## Prompting (LLM-ready)
- Analyst system prompt (summary):
  - You analyze a candidate’s resume and a job description. Output a concise set of talking points and a cover letter outline. Use only grounded facts from provided context. Avoid fabrications.
- Analyst output schema:
  - roleSummary, companySummary, strongMatches[], riskMitigations[], outline{opening, body[], closing}
- Writer system prompt (summary):
  - You are a professional cover letter writer. Draft compelling paragraphs aligned to the outline and evidence. Keep it concise, clear, and tailored.
- Editor system prompt (summary):
  - You are an expert editor. Enforce tone, remove fluff, correct style, ensure ATS-friendliness, maintain evidence.
- JIT retrieval notes:
  - Provide JD highlights and Chroma snippets as context to each agent. Limit to top-K to avoid drift.

## Files to Add/Update (no coding here; instructions only)
- app/features/
  - cover_letter_orchestrator.py – orchestrator with steps (validate → fetch resume → JD → analysis → writing → edit → assemble → persist → respond)
- app/agents/
  - cover_letter/
    - analyst_agent.py – crafts outline/talking points
    - writer_agent.py – drafts paragraphs
    - editor_agent.py – refines content
- app/services/
  - cover_letter_service.py – CRUD-adjacent utilities (load resume, optionally persist cover letter artifacts)
- app/api/v1/endpoints/
  - cover_letters.py – POST /api/v1/cover-letters/strategic-create
    - Body: { resumeId: str, jobDescriptionUrl: str, prompt?: str }
    - Response: { status, message, data: { coverLetter: {...} } }
- app/schemas/
  - Extend or add schemas to represent response payload (either reuse CoverLetterTypes and JobProfileDetails or add StrategicCoverLetterResponse)
- tests/
  - test_strategic_cover_letter_simple.py – happy path
  - test_strategic_cover_letter_components.py – agent components
  - test_strategic_cover_letter_endpoint.py – API contract

## Testing Strategy
- Unit tests
  - Analyst agent: given JD + resume snippets, returns outline with grounded matches.
  - Writer agent: produces opening/body/closing; respects optional prompt (tone or priority).
  - Editor agent: enforces word count and tone; removes ungrounded claims.
  - Assembler: builds finalContent; placeholders are well-formed.
- Integration tests
  - End-to-end generation with mocked JD fetch and fixed resume from fixtures; validates envelope and required fields.
  - Retrieval sanities: Chroma returns at least N snippets; handle empty gracefully.
- API tests
  - POST /api/v1/cover-letters/strategic-create with valid inputs → 201/200 and correct shape.
  - Invalid resumeId → 404; bad JD URL → 422/502; model overload (503) → map to 503 with retry hint.

## Error Handling
- 404 if resume not found
- 422 if invalid URL
- 502/503 for upstream JD fetch or LLM transient errors (with retries/backoff and a user-facing retry message)
- Graceful degradation if Chroma is empty: still generate with resume summary (lower confidence)

## Observability
- Structured logs: input IDs, truncation counts, retrieval sizes, token usage estimates (if available)
- Attach plan artifacts to logs for debugging (redact PII as needed)

## Performance & Limits
- Limit retrieval context size (e.g., top 8–12 snippets, max tokens)
- Keep total output <= ~600–800 words
- Add exponential backoff with jitter for LLM and scraping tools

## Acceptance Criteria
- API accepts (resumeId, jobDescriptionUrl, optional prompt) and returns a valid cover letter payload including finalContent and structured fields.
- Content is grounded (references present in resume/JD) and passes basic validations (non-empty opening/body/closing; reasonable length).
- Works with the same Chroma + JD tools as Strategic Resume Analysis.
- Tests cover happy path + basic errors (404, 422, 503).

## Rollout Plan
1) Implement orchestrator + agents + endpoint behind a feature flag if desired.
2) Add tests; ensure green locally and in CI.
3) Manual smoke test using one known resume and one live JD URL.
4) Monitor logs for transient 503s; adjust retry/backoff if needed.

## Risks & Alternatives
- Risk: JD site blocks scraping → return helpful 502 and allow manual JD paste as fallback input.
- Risk: Chroma collection missing → degrade to resume summary-based generation.
- Alternative: One-shot LLM prompt (no multi-agent) for simplicity; lower control/quality.

## LLM-Executable Checklist
- [ ] Create endpoint POST /api/v1/cover-letters/strategic-create (body: resumeId, jobDescriptionUrl, prompt?)
- [ ] Implement cover_letter_orchestrator with steps (validate → retrieve → analyze → write → edit → assemble → respond)
- [ ] Reuse resume + JD tools from Strategic Resume Analysis
- [ ] Add agents (analyst, writer, editor) with prompts and clear IO contracts
- [ ] Add/extend Pydantic response schemas
- [ ] Add unit/integration/API tests
- [ ] Add retries/backoff for JD fetch and LLM 429/500/503; surface 503s properly
- [ ] Document env/config toggles if needed (e.g., model selection, timeouts)
