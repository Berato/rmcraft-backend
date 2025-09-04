# Resume Creation from PDF — Implementation Plan

This document is a complete, precise, and actionable implementation plan that an LLM-based coding agent can follow to implement the "Resume Creation from PDF" feature end-to-end. It prescribes a dual-agent pipeline (Planning Agent → Schema Agent), exact message-part contracts, tools, session state keys, robust parsing rules, logging, and rollout steps.

Follow this plan verbatim — do not assume implicit behavior. All code-level behaviors are explicit so an engineer or another LLM can implement the feature in one pass.

## 1. Goal / Success Criteria
- Input: extracted PDF text (plain UTF-8), PDF metadata (filename, size, page count, extraction method).
- Output: JSON matching `ResumeExtractionOutputSchema` with keys: `name`, `summary`, `experiences`, `skills`, `projects`, `education`, `contact_info`.
- The pipeline must be deterministic: the Schema Agent must always receive the Planning Agent's output (as the first message part) and the full PDF text (as another part).
The Schema Agent must receive the Planning Agent's output (as the first message part) and the full PDF text as another part; the Schema Agent is responsible for producing complete JSON that conforms to the schema.

## 2. High-level Architecture

- Two LLM agents run sequentially for each request:
  1. Planning Agent (tools enabled) — analyzes PDF content, identifies sections, calls tools for chunked analysis, and writes a planning artifact to session state via a `store_analysis_result` tool.
  2. Schema Agent (no tools) — receives the Planning Agent output as the first user message part (JSON or raw text), plus metadata and full PDF text as subsequent parts, and returns structured JSON matching the output schema.

- Runner behavior: use a Runner (or equivalent) to run each agent. Merge any structured `ev.output` into `session.state` as events stream in; the final agent response should be parsed robustly.

## 3. Data Contracts

3.1 Planning output (planning artifact): a JSON object with the following recommended shape — it is intentionally permissive so the planner can return richer analysis:

{
  "identified_sections": ["contact", "summary", "experience", "education", "skills", "projects"],
  "analysis_summary": "Short human-readable summary of the document (70-200 chars)",
  "content_analysis": {
    "section_summaries": { "experience": "...", "education": "..." },
    "keywords": ["React","Python","Kubernetes"],
    "raw_chunks": ["..."]
  },
  "planning_text": "(optional) raw textual analysis output if planner didn't emit JSON"
}

3.2 Final output: implement or reuse `ResumeExtractionOutputSchema` with fields (examples):
- `name`: string
- `summary`: string
- `contact_info`: object (email, phone, linkedin, website, address)
- `experiences`: array of { id, company, title, start_date, end_date, location, achievements: [string], raw_text }
- `skills`: array of { id, name, category? , level? }
- `projects`: array of { id, name?, description, technologies: [string], link? }
- `education`: array of { id, institution, degree, start_date?, end_date?, raw_text }

IDs must be stable and unique per response (e.g., `exp_1`, `skill_1`), and dates normalized to `YYYY-MM` or `YYYY` where possible.

## 4. Tools (FunctionTool) and Their Contracts

Provide these tools to the Planning Agent only. Each tool must accept a `tool_context` parameter that includes `tool_context.session` (the session object) and must write to `tool_context.session.state` when appropriate.

1) store_analysis_result(analysis_summary: str, identified_sections: List[str], content_analysis: str, tool_context=None) -> Dict
- Persists analysis into `tool_context.session.state` keys:
  - `analysis_summary` (str)
  - `identified_sections` (list)
  - `content_analysis` (str or dict)
  - `analysis_complete` = True

2) analyze_resume_section(section_text: str, section_type: str, tool_context=None) -> Dict
- Performs a focused analysis for a section and returns structured hints (keywords, sketch of extracted fields). Returned dicts may be merged into session state.

3) (Optional) google_search(query: str, tool_context=None) -> Dict
- For external enrichment. Must never return or persist PII from external queries into logs without redaction.

## 5. Session & State Model

Session is ephemeral per request. Required session state keys (set defaults prior to agent runs):
- `pdf_content` (string)
- `pdf_metadata` (dict)
- `planning_analysis` (dict)
- `analysis_summary` (string)
- `identified_sections` (list)
- `content_analysis` (string/dict)
- `analysis_complete` (bool)

Notes:
- Always set safe defaults with `session.state.setdefault(key, default)` before running agents to prevent templating or instruction interpolation errors.
- Do not rely on placeholders (e.g., using `{identified_sections}` inside instructions). Instead, pass planning output as explicit message parts to the Schema Agent.

## 6. Message Part Contract and Agent Instructions (copy-paste ready)

6.1 Planning Agent instruction (exact):

"""
You are a Planning Agent. You will receive the full PDF text as a single user content part (metadata+pdf text combined).
Your responsibilities:
- Identify explicit resume sections and section boundaries (contact, summary, experience, education, skills, projects).
- For each section you identify, call `analyze_resume_section(section_text, section_type)` to produce structured hints.
- Aggregate your analysis into a JSON object and call `store_analysis_result(analysis_summary, identified_sections, content_analysis)` before finishing.
- If you cannot produce valid JSON, return a final plain-text analysis (but still call `store_analysis_result` with a text `content_analysis`).
Be thorough and conservative: prefer extra structure (section start/end offsets, short summaries, tokens) rather than attempting to fully extract final resume objects.
"""

6.2 Schema Agent instruction (exact):

"""
You are a Schema Agent. You will receive three message parts in this order:
1) The Planning Agent output as raw JSON string (or raw text). This is the authoritative primary input. Parse it and base extraction on it.
2) A small metadata part describing PDF filename, size, page count.
3) The full PDF text as plain user content.

Your task:
- Parse the planning JSON (or raw analysis text) and use it to guide structured extraction into the exact `ResumeExtractionOutputSchema`.
- If the planning JSON is missing fields like `identified_sections`, gracefully fallback to analyzing the full PDF text.
- Return ONLY valid JSON that strictly conforms to the schema. Do not include commentary or extra top-level fields.
- Use deterministic rules for IDs (e.g., `exp_1`, `skill_1`) and normalize dates to `YYYY-MM` or `YYYY`.
"""

Implementation note: Do NOT attempt to embed the entire PDF as a templated string inside the instruction. Use message parts as above.

## 7. Runner & Parsing Strategy (robust, deterministic)

Implement `run_single_agent(agent, message_content, session, session_service, user_id, session_id)` with the following behavior:

1) Create Runner with the agent, app_name, session_service.
2) Stream events from `runner.run_async(...)`. For each event `ev`:
   - If `ev.output` exists and is a dict: merge keys into `session.state` but do NOT overwrite existing keys unless they are empty.
   - If `ev.output_key` is present and `ev.output` exists, set `session.state[ev.output_key] = ev.output`.
3) When `ev.is_final_response()` is True, collect `ev.content.parts` texts into a list `final_texts`.
4) Parsing attempts (in order):
   a) If there's exactly one part: attempt `json.loads(part_text)`.
   b) Try to parse each part independently as JSON.
   c) Search the concatenated text for the first top-level JSON object using a greedy regex `r"(\{[\s\S]*\})"` and attempt `json.loads` on the capture.
   d) If still failing, return the raw joined text as fallback.

Always log (redacted) the final_texts for debugging.

## 8. Logging, Debugging & Privacy

- Keep an append-only `server.log` file with clearly labeled sections:
  - `=== PLANNING RESULT RAW ===` (only if not containing PII) — prefer to log a redacted or summarized planning JSON.
  - `=== SCHEMA INPUT PARTS ===` — store size/length of parts but redacted content.
  - `=== AGENT FINAL CONTENT ===` — store truncated previews (e.g., first 2000 chars) of each part.

- Redaction policy: do not log full PDF text. When logging content, redact email addresses and phone numbers (replace with `[REDACTED_EMAIL]`, `[REDACTED_PHONE]`).

## 9. Logging, Debugging & Privacy

- Keep an append-only `server.log` file with clearly labeled sections:
  - `=== PLANNING RESULT RAW ===` (only if not containing PII) — prefer to log a redacted or summarized planning JSON.
  - `=== SCHEMA INPUT PARTS ===` — store size/length of parts but redacted content.
  - `=== AGENT FINAL CONTENT ===` — store truncated previews (e.g., first 2000 chars) of each part.
  - `=== POST-PROCESS FALLBACK ===` — store the fallback candidates chosen (first N entries).

- Redaction policy: do not log full PDF text. When logging content, redact email addresses and phone numbers (replace with `[REDACTED_EMAIL]`, `[REDACTED_PHONE]`).

## 10. Error Handling and Resilience

- Timeouts: set a per-agent timeout (e.g., 30s) and fail gracefully with structured error JSON.
- JSON parse failures: treat as planner raw text and still pass the raw text as the first part to Schema Agent.
- Partial outputs: if Schema Agent returns top-level resume fields instead of wrapped `extracted_resume`, accept both shapes.
- If both agents fail to yield any usable data, return `success: False` and include a safe `metadata` and a terse `error` message.

## 9. Error Handling and Resilience

- Timeouts: set a per-agent timeout (e.g., 30s) and fail gracefully with structured error JSON.
- JSON parse failures: treat as planner raw text and still pass the raw text as the first part to Schema Agent.
- Partial outputs: if Schema Agent returns top-level resume fields instead of wrapped `extracted_resume`, accept both shapes.
- If both agents fail to yield any usable data, return `success: False` and include a safe `metadata` and a terse `error` message.

## 10. Quality Gates (pre-merge checklist)

- Lint and typecheck: project linters pass.
- Manual live test: run the curl acceptance test against a dev server and verify `server.log` contains the labeled debug sections.

## 11. Rollout & Monitoring

- Start behind a feature flag. Enable for limited users.
- Collect anonymized extraction metrics for first N requests: counts of array lengths and error rates.
- If model drift or poor quality, adjust `generate_content_config.temperature` for the Schema Agent and reinforce instructions to the Schema Agent to produce arrays.

## 12. Implementation Checklist (one-shot actionable steps for the LLM implementer)
1. Add/verify `types.Part`, `types.Content` usage; ensure message parts are created and passed in the correct order.
2. Implement `FunctionTool` wrappers for `store_analysis_result` and `analyze_resume_section` and register them with the Planning Agent.
3. Initialize `session.state` defaults for all required keys before running agents.
4. Implement `run_single_agent` with streaming event handling, merging `ev.output` into `session.state`.
5. Implement parsing strategy exactly as specified in Section 7.
6. Persist `planning_dict` into `session.state` and always pass it (raw JSON string or `planning_text`) as the first part to the Schema Agent.
7. Implement Schema Agent with `output_schema` and `response_mime_type="application/json"`.
8. Implement logging (redaction-first) to `server.log` labeled sections.
9. Run a manual live acceptance test via curl against a dev server to verify end-to-end behavior.

## 13. Example snippets and exact phrases to use in instructions

- For the Schema Agent first-part sentence (exact):
  "The first user message part contains the PLANNING AGENT output as raw JSON. Parse that JSON and use it as your primary analysis input. If fields like `identified_sections`, `analysis_summary`, or `content_analysis` are missing, fall back to analyzing the provided PDF text (also included in the message parts)."

- Example deterministic ID rule:
  - `for i, e in enumerate(experiences): e['id'] = f"exp_{i+1}"`

## 14. Edge cases & mitigation
- Very large PDFs: chunk for the Planning Agent, but pass a summary/planning artifact to the Schema Agent (do not pass > 200KB raw text as a single part).
- Non-English resumes: detect language; if non-English, either reject or call a translation step before extraction.
- Badly formatted/one-column text: use conservative extraction and prefer concise matches.

## 17. Security & Privacy
- Do not write raw PDF content or PII to logs. Replace emails/phones with `[REDACTED]` before persisting logs.
- Expire `session.state` after request completion.

## 18. Follow-ups and Improvements
- Add a lightweight QA loop where suspicious or low-confidence extractions trigger a human review workflow.
- Add schema-level validation tests that ensure dates parse to acceptable formats.
- Add a user-facing confidence score per section based on planning_agent hints and schema agent certainty.

---

This document is intended to be copy-pasted directly into the repository and used as the single authoritative plan for implementing the feature. If you want, I can now implement these steps directly in the repository (create/update files, add tests, and run the smoke runner). Mark which of the checklist items you'd like me to execute first.

