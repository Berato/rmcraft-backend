# Strategic Cover Letter Database Persistence Implementation Plan

## Goal

Add a complete implementation plan to persist a generated strategic cover letter to the project's database when it is produced by the orchestrator workflow. This document contains all context, data shapes, implementation steps, test cases, and edge-case handling an LLM agent (or developer) would need to implement the feature end-to-end.

---

## Requirements Checklist

- [ ] Persist generated strategic cover letters to the database automatically when generation succeeds.
- [ ] Define a `CoverLetter` SQLAlchemy model compatible with existing project conventions.
- [ ] Implement a service function `save_cover_letter` in `app.services.cover_letter_service` that validates, formats, sanitizes, and persists the cover letter in a transactional way.
- [ ] Wire persistence into `app.features.cover_letter_orchestrator.cover_letter_orchestrator` so that after successful assembly and editing the cover letter is saved and its DB id (or metadata) included in the orchestrator response.
- [ ] Add or update API endpoint(s) to return DB identifiers and status; provide an opt-out flag to not persist (backwards-compatible option).
- [ ] Add unit and integration tests (service-level, orchestrator-level, endpoint-level) and migration scripts for DB schema changes.
- [ ] Add basic monitoring/logging and idempotency considerations.

---

## High-level approach

1. Create a new SQLAlchemy model `CoverLetter` in `app.models` following existing conventions (string primary key, camelCase DB column names where the repo already uses that pattern, timestamps, JSON fields where appropriate).
2. Extend `app.services.cover_letter_service` with a `save_cover_letter(cover_letter_data: dict, db: Session) -> CoverLetter` function. This will call the existing validation, formatting, and sanitization helpers, then persist the record.
3. Add a small persistence call in the orchestrator: after `final_content` is assembled and response_data built, call `save_cover_letter(...)`. Capture the returned DB id and include `jobProfileId`/`coverLetterId` (or similar) in the orchestrator response.
4. Add tests to verify persistence and rollback on failures.
5. Add a DB migration (Alembic or raw SQL) to create the `cover_letters` table. The migration should be reversible.

---

## Why this design

- Follows repository patterns: SQLAlchemy models in `app/models`, Session management from `app/db/session.py`.
- Keeps business logic in service layer (`app/services/cover_letter_service.py`).
- Orchestrator remains responsible for generation flow and simply calls the service to persist.
- Provides an opt-out save flag for flexibility and testability.

---

## Data shapes and field mapping

Proposed SQLAlchemy `CoverLetter` model (fields and types):

- id: String primary key (UUID string)
- title: String
- jobDetails: JSON (stores title, company, url)
- openingParagraph: String / Text
- bodyParagraphs: JSON (array of strings)
- companyConnection: String (nullable)
- closingParagraph: String / Text
- tone: String
- finalContent: Text (full assembled letter)
- resumeId: String (FK -> resumes.id) indexed
- jobProfileId: String (nullable) indexed
- wordCount: Integer
- atsScore: Integer
- metadata: JSON (optional free-form metadata: analysis snippets, agent run ids, sessions)
- createdAt: DateTime
- updatedAt: DateTime

Notes and mapping to existing code:
- The repository already has a `Resume` model (`app/models/resume.py`) using camelCase column names like `userId`, `createdAt` etc — follow the same naming style.
- `app.services.cover_letter_service` already provides `validate_cover_letter_data`, `format_cover_letter_for_storage`, `sanitize_cover_letter_content` helpers — reuse them in `save_cover_letter`.

Example JSON payload that the orchestrator currently builds (from `app/features/cover_letter_orchestrator.py`):

```json
{
  "title": "Strategic Cover Letter",
  "jobDetails": {"title": "...", "company": "...", "url": "..."},
  "openingParagraph": "...",
  "bodyParagraphs": ["para1","para2"],
  "companyConnection": "...",
  "closingParagraph": "...",
  "tone": "professional",
  "finalContent": "...",
  "resumeId": "<resume-id>",
  "createdAt": "...",
  "updatedAt": "...",
  "wordCount": 320,
  "atsScore": 8
}
```

This dict should be accepted by `save_cover_letter` and mapped to the DB model.

---

## Implementation tasks (step-by-step)

### 1. Add model `app/models/cover_letter.py` (SQLAlchemy)
- Use the same Base as other models (`from app.db.session import Base` or `declarative_base()` consistent with `theme.py`).
- Use `default` generator for id (uuid). Include indexes on `resumeId` and `jobProfileId`.
- Example columns: see Data shapes above.

### 2. Add DB migration
- If the project uses Alembic, create an Alembic revision with upgrade/downgrade creating/dropping `cover_letters` table. If there is no Alembic, provide raw SQL migration file and instructions.
- Ensure `resumeId` is NOT NULL if you want enforced link; otherwise allow nullable for flexibility. Prefer NOT NULL to ensure traceable provenance.

### 3. Add service persistence function
- File: `app/services/cover_letter_service.py`
- Add:
  - `def save_cover_letter(cover_letter_data: Dict[str, Any], db: Session, upsert: bool = False) -> Dict[str, Any]`
  - Steps inside: validate -> format -> sanitize finalContent and paragraphs -> create model instance -> add to db session -> commit -> refresh -> return persisted record (as dict/pydantic)
  - Handle DB exceptions: rollback and re-raise a clear exception.
  - If `upsert` is True, optionally check for existing cover letters with a unique constraint (resumeId + jobDetails.url) and update instead of insert.

### 4. Wire orchestrator to save
- Update `app/features/cover_letter_orchestrator.py` right after building `response_data` (before returning) to call the new service function. Example:
  ```python
  from app.db.session import SessionLocal
  from app.services.cover_letter_service import save_cover_letter
  
  db = SessionLocal()
  try: 
      saved = save_cover_letter(response_data, db)
      response_data['coverLetterId'] = saved.id
  finally: 
      db.close()
  ```
- Make this call optional via an `optional` parameter (e.g., `save_to_db=True`) added to `cover_letter_orchestrator` signature for backwards-compatibility and testing. Default to True to meet the request.

### 5. Update API endpoint
- Add an optional boolean `saveToDb` (default True) to `StrategicCoverLetterRequest` in `app/api/v1/endpoints/cover_letters.py` and pass it through to the orchestrator. 
- If saving is successful, include returned DB id in response payload (e.g., `jobProfileId` or a new `coverLetterId` field).
- Keep the existing response model compatible; if adding new fields, make them Optional in `StrategicCoverLetterResponse`.

### 6. Tests
- Unit test for `save_cover_letter`: verifies that valid data is persisted and sanitized, and invalid data raises expected error. Use a temporary/test DB (or in-memory SQLite) session.
- Orchestrator-level test: mock the AI agent runs (existing tests already patch agent functions) and assert that after `cover_letter_orchestrator` runs, a DB row exists (or `save_cover_letter` was called). Add a test for both default behavior (save) and `saveToDb=False`.
- Endpoint-level test: update `tests/test_strategic_cover_letter_endpoint.py` to assert `coverLetterId` (or new field) appears when saving is enabled.

### 7. Logging and monitoring
- Log a debug/info message on successful save: cover-letter id, resumeId, wordCount.
- Log errors with enough context to reproduce failures (resumeId, job URL, orchestrator session id), but avoid persisting PII in logs.

### 8. Migration and deployment notes
- Ensure migrations are applied before deploying the orchestrator change.
- Add a short database migration run in CI (if exists) to validate migration correctness.

---

## Error handling, transactions, and idempotency

- Always use a DB transaction scope: create session, add instance, commit, refresh, close.
- On any exception, rollback and raise a domain-level exception to the orchestrator. The orchestrator should catch persistence errors and decide whether to return the generated cover letter (but not persisted) or fail the request. Recommended: do not hide generation result when persistence fails; return the generated cover letter but include a `persistenceError` field or log the error and return 201 with a warning. This keeps user experience resilient.
- Idempotency: implement a `resumeId + jobDetails.url` unique index/constraint (optional) or implement `upsert` logic. If unique constraint is used, save should handle IntegrityError and either return existing row or update it depending on configuration.

---

## Example implementation sketch (service function)

This sketch should be translated into `app/services/cover_letter_service.py`. It is intentionally descriptive; exact code style should match project conventions.

1. validate input using `validate_cover_letter_data`
2. `cover_letter_data = format_cover_letter_for_storage(cover_letter_data)`
3. `cover_letter_data['finalContent'] = sanitize_cover_letter_content(cover_letter_data['finalContent'])`
4. create model instance with mapped fields and `db.add(instance)`
5. commit and refresh
6. return instance

---

## Tests to add (detailed)

### 1. `tests/unit/test_cover_letter_service.py`
- `test_save_cover_letter_happy_path`: uses a temporary DB session, calls save_cover_letter, asserts persisted values and types.
- `test_save_cover_letter_invalid_data`: ensure invalid data is rejected by validation helper.
- `test_sanitize_final_content_called`: verify that whitespace / harmful content is sanitized.

### 2. `tests/integration/test_orchestrator_persistence.py`
- Patch or mock ADK agents to produce deterministic analysis/writing/editing results (existing test fixtures do this). Call orchestrator and assert DB row count increased and returned payload includes `coverLetterId`.
- Also test `saveToDb=False` path: no DB rows should be created.

### 3. `tests/test_strategic_cover_letter_endpoint.py`
- Add a test that calls the endpoint through the function `create_strategic_cover_letter` and asserts the response contains created DB id when saving is enabled.

Make tests use the project's existing test DB (`test.db`) or in-memory DB backed by SQLAlchemy engine created specifically for test runs.

---

## Migration SQL (example)

```sql
CREATE TABLE cover_letters (
  id VARCHAR PRIMARY KEY,
  title VARCHAR,
  jobDetails JSON,
  openingParagraph TEXT,
  bodyParagraphs JSON,
  companyConnection TEXT,
  closingParagraph TEXT,
  tone VARCHAR,
  finalContent TEXT,
  resumeId VARCHAR REFERENCES resumes(id),
  jobProfileId VARCHAR,
  wordCount INTEGER,
  atsScore INTEGER,
  metadata JSON,
  createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_cover_letters_resumeId ON cover_letters(resumeId);
CREATE INDEX idx_cover_letters_jobProfileId ON cover_letters(jobProfileId);
```

If using Alembic, create the equivalent revision using SQLAlchemy `op.create_table`.

---

## Acceptance criteria

- When `cover_letter_orchestrator` runs and completes successfully, by default a row is persisted in the `cover_letters` table containing the full generated content and metadata.
- The API `POST /api/v1/cover-letters/strategic-create` returns the generated cover letter payload and a new DB id (or indicates the save result). Tests for both saving and opt-out exist and pass.
- Persistence failures do not silently drop the generated content; the endpoint must either return a clear error or return the generated content with a warning/persistenceError field.

---

## Assumptions made

- The project uses SQLAlchemy with `app/db/session.py` and can obtain a DB session via `SessionLocal()`.
- The repo does not currently have a `cover_letters` table or model. If it exists, adjust field names to match.
- The project prefers camelCase column naming conventions (see `app/models/resume.py` and `app/models/theme.py`). Use consistent naming.
- Tests will run against a local/test DB created by CI or test fixtures; if not, the LLM should add in-memory SQLite usage for tests.

---

## Next steps for an LLM agent implementing this

1. Create `app/models/cover_letter.py` and run linter/typechecker.
2. Create and apply DB migration (or produce migration file for maintainers).
3. Implement `save_cover_letter` in `app/services/cover_letter_service.py` reusing existing helpers.
4. Wire orchestrator to call `save_cover_letter` with `save_to_db=True` default.
5. Update API schema to accept optional `saveToDb` and return persisted id.
6. Add unit/integration tests and run test suite; fix any failing tests.
7. Add minimal docs/README entry summarizing the persistence behavior and opt-out switch.

---

## Contact points in the codebase (helpful references)

- Orchestrator workflow: `app/features/cover_letter_orchestrator.py`
- Agents: `app/agents/cover_letter/analyst_agent.py`, `writer_agent.py`, `editor_agent.py`
- Service helpers: `app/services/cover_letter_service.py` (validation / format helpers already present)
- API endpoint: `app/api/v1/endpoints/cover_letters.py`
- DB session & Base: `app/db/session.py`
- Existing models: `app/models/resume.py`, `app/models/theme.py`

---

**Addendum:** Sample SQLAlchemy model and function signatures are included in the body above — use them as the precise contract when implementing code.

This plan is complete and intended to be machine-actionable: it includes model shapes, migrations, service method contract, orchestration integration point, tests, and acceptance criteria.
