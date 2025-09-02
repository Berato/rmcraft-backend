# Schema Assembler Plan

This document is an actionable, copy-pasteable plan an LLM agent or engineer can follow to convert the current multi-agent workflow into: schema-less generator sub-agents + a single Schema Assembler that validates, repairs, and emits the final Pydantic-shaped resume object.

---

## Quick checklist

```
- [x] Create this plan in `docs/`
- [ ] Inventory agents that use `output_schema`
- [ ] Remove `output_schema` from sub-agents (keep only when absolutely required)
- [ ] Standardize prompts and generate configs for sub-agents (JSON-only, low temperature)
- [ ] Implement `schema_assembler.py` that validates, repairs, and builds final Pydantic object
- [ ] Wrap synchronous sub-agents as `AgentTool` where needed
- [ ] Add unit, fuzz, and integration tests for assembler and generators
- [ ] Add metrics, structured logging, and rollout/monitoring plan
```

---

## Purpose

Avoid ADK runtime warnings and brittle behavior caused by mixing `output_schema` with tools/transfers. Instead make sub-agents simple JSON generators and centralize Pydantic enforcement and repair in a single, deterministic component (Schema Assembler).

This reduces surprising runtime reconfiguration, makes repairs explicit and testable, and isolates LLM repair calls to a well-defined, low-latency, low-retry path.

---

## High-level strategy (what & why)

- Sub-agents become "generators": they produce JSON-like fragments guided by strict prompt templates and deterministic generation settings.
- The Schema Assembler reads the session state (or receives the fragments directly), cleans/parses each fragment, validates it with Pydantic, performs deterministic coercions, optionally requests a single deterministic LLM repair, and produces a final validated Pydantic object with diagnostics.
- Any sub-agent that must use tools or be transferable should NOT use `output_schema`.

---

## Contract for the Schema Assembler

- Inputs:
  - Map of session keys → raw values produced by sub-agents (strings, dicts, or pydantic models). Typical keys: `experiences`, `skills`, `projects`, `summary`, `design_brief`, `jinja_template`, `css_styles`, etc.
  - Original resume and JD context (optional) to disambiguate repairs.

- Output:
  - A single dict or Pydantic model matching `ResumeSchemas` with the keys: `experiences`, `skills`, `projects`, `summary`, `education`, `contact_info`, `design_brief`, `jinja_template`, `css_styles`, `cloudinary_url`.

- Diagnostics:
  - For each sub-piece: original fragment, repairs applied (coercion|LLM|fallback), number of retries, final status (OK|PARTIAL|FAILED).

- Failure modes:
  - Unrepairable fragment → safe default applied (empty list/dict/""), diagnostic recorded.
  - Excessive repair attempts → escalate for human review.

---

## Deterministic validation & repair algorithm

1. Normalize input:
   - If value is a Pydantic model, call `.model_dump()`.
   - If value is a string: run `clean_json_response()` (strip markdown, extract JSON) and attempt `json.loads()`.
2. Attempt `pydantic.parse_obj` for the target schema.
3. If validation succeeds: accept and record `OK`.
4. If validation fails: run a deterministic coercion pass:
   - `None` → `""` for required strings.
   - Single object → `[object]` if schema expects list.
   - Convert numeric-like strings to numbers when schema expects numbers.
   - Missing lists → `[]`, missing dicts → `{}`.
5. Re-validate. If success → log `repaired: coercion` and accept.
6. If still failing: run a single deterministic LLM repair attempt (temperature=0.0) using the repair prompt (see templates). Require JSON-only output.
7. Re-validate repaired output. If success → log `repaired: LLM` and accept.
8. If still failing: apply safe fallback (empty list/dict/""), log `fallback`, continue.

Notes: limit LLM repairs to 1 retry per fragment to control cost and latency.

---

## Sub-agent (generator) guidelines

- Generation config:
  - `temperature = 0.5`
  - `response_mime_type = "application/json"`.
  - `thinking_config`: `include_thoughts=True`

- Prompt best-practices:
  - Explicit: "Return ONLY a JSON object. Start with `{` and end with `}`. No markdown, no commentary."
  - Provide a minimal example showing empty defaults (strings `""`, lists `[]`).
  - Encourage defensive defaults in examples to reduce repairs.

- If a sub-agent needs tools or transfers, do NOT set `output_schema` for it.

Example generator instruction (non-code):

"You are a JSON-only generator. Return ONLY a JSON object with the exact structure shown. Use empty strings for unknown string fields and empty arrays for unknown lists. Example minimal output when unknown: { \"projects\": [] }"

---

## LLM repair prompt template (single-shot)

- Settings: temperature=0.0, response_mime_type="application/json", JSON-only output.

- Template (use literal insertion of fragment and example):

```
You will be given a JSON fragment and a target minimal example. Return ONLY a corrected JSON fragment that strictly matches the example shape. Use empty strings ("") for missing strings and empty arrays ([]) for missing lists. No extra text.

Target example:
{ "projects": [{ "id": "proj_1", "name": "Project Name", "description": "Description", "url": "" }] }

Fragment to fix:
<RAW_FRAGMENT_HERE>

Return only the corrected JSON fragment.
```

---

## AgentTool & coordination guidance

- Wrap any sub-agent that must be synchronously invoked as an `AgentTool` and call it explicitly from a coordinator or the Schema Assembler. This avoids LLM-driven transfers and keeps behavior explicit.
- Keep schema-less those sub-agents that must use `tools` or be transferable.

---

## Testing plan

- Unit tests:
  - Happy path: well-formed fragments → assembler accepts unchanged.
  - Broken-field cases: `projects[0].url = None`, `projects` as string, markdown-wrapped JSON → assembler repairs/coerces.

- Fuzz tests:
  - Random malformed fragments → assembler must produce valid Pydantic or documented fallback.

- Integration tests:
  - Mock LLM with canned generator outputs and test full `full_workflow` run to ensure final Pydantic is valid.

- Harness notes:
  - Mock the LlmAgent outputs for deterministic tests.
  - Assert diagnostics structure and fields repaired.

---

## Metrics, logging, and monitoring

- Metrics to collect:
  - `schema_pass_rate` (percent runs needing zero repairs).
  - `repair_count_per_run` and `repair_count_per_field`.
  - `llm_repair_invocations` and `llm_repair_success_rate`.
  - `pydantic_exception_count` (goal: 0 in staging).

- Logging:
  - Structured JSON logs per repair: `{ field, original_fragment_hash, repair_type, repaired_fragment_hash, status }`.
  - Avoid writing secrets to logs (mask emails, tokens).

- Alerts:
  - Trigger when `repair_rate` or `fallback_rate` exceeds threshold (e.g., 5% in staging).

---

## Rollout plan

- Dev: implement `schema_assembler.py`, add unit/fuzz tests, run locally against mocked LLM.
- Staging: route real runs to staging for 1–2 weeks and gather metrics.
- Prod: enable after `schema_pass_rate` ≥ 95% and low LLM repair usage.
- Rollback: keep prior pipeline toggled via config flag.

---

## Acceptance criteria

- Unit + integration tests pass.
- Staging `schema_pass_rate` ≥ 95%.
- `pydantic` validation exceptions = 0 in staging.
- Structured diagnostics for all repairs.
- Runtime warnings about `output_schema` for sub-agents are gone because sub-agents no longer use `output_schema`.

---

## Minimal next actions for an LLM agent (one-liner)

List every `LlmAgent` constructor in `app/agents/resume/strategic/strategic_resume_agent.py` that sets `output_schema` and produce a code patch that:

1. Removes `output_schema` from each sub-agent listed (preserve `output_key` where helpful).
2. Adds a new file spec `app/agents/resume/strategic/schema_assembler.py` implementing the validation & repair algorithm above (initial implementation can call Pydantic models from `app.schemas.ResumeSchemas`).

---

## Deliverables expected from the LLM agent

- A unified patch removing `output_schema` from sub-agents.
- New `schema_assembler.py` with deterministic repair logic and diagnostics.
- Prompt templates for generator agents and the LLM repair prompt.
- Unit, fuzz, and integration test suites with sample bad inputs and expected outputs.
- Monitoring/metrics stub (names, thresholds).

---

If you want me to proceed I can either: (A) produce the PR-ready patch that removes `output_schema` and adds `schema_assembler.py` plus tests, run tests, and iterate; or (B) generate the exact prompt and test-case artifacts only. Tell me which next step you prefer.
