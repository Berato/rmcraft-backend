# Theme DB Sync Implementation Plan (Prisma → Python)

Purpose: Bring the Python ORM, CRUD, and service code into full alignment with the Prisma-managed database schema for `themes` and `theme_packages`. This plan is the complete, file-specific context an LLM needs to implement and verify the fix end-to-end.

## Truth Source Summary (Prisma schema)

Tables
- themes (mapped by Prisma `@@map("themes")`)
- theme_packages (mapped by Prisma `@@map("theme_packages")`)

themes columns
- id (pk, String)
- name (String, UNIQUE)
- description (String?, nullable)
- type (enum: RESUME | COVER_LETTER)
- template (String, required)
- styles (String, required)
- previewImageUrl (String?, nullable)
- createdAt (timestamp, default now())
- updatedAt (timestamp, auto-updated)

theme_packages columns
- id (pk, String)
- name (String, required)
- description (String?, nullable)
- resumeTemplateId (String, FK → themes.id, onDelete=RESTRICT, onUpdate=CASCADE)
- coverLetterTemplateId (String, FK → themes.id, onDelete=RESTRICT, onUpdate=CASCADE)
- createdAt (timestamp, default now())
- updatedAt (timestamp, auto-updated)

Indexes and constraints
- themes.name is UNIQUE
- theme_packages UNIQUE(resumeTemplateId, coverLetterTemplateId)
- theme_packages INDEX(resumeTemplateId)
- theme_packages INDEX(coverLetterTemplateId)

Important naming note
- Column names in the database are camelCase for some fields (e.g., resumeTemplateId, coverLetterTemplateId, previewImageUrl). The Python app must respect these exact column names at the SQL layer.

## Current Drift (Python vs DB)

Observed in `app/models/theme.py`:
- ThemePackage uses snake_case columns: `resume_template_id`, `cover_letter_template_id` (DB expects camelCase).
- Theme model is missing `previewImageUrl` column.
- Theme.name is indexed but not unique.
- ThemePackage lacks the UNIQUE pair constraint and helpful indexes.
- FKs lack explicit referential actions (RESTRICT/CASCADE) in the ORM mapping.
- Timestamps use Python `datetime.utcnow` defaults; in DB they’re generated/updated server-side.

Elsewhere (usage):
- `app/services/theme_service.py` and `app/features/theme_generator.py` instantiate `ThemePackage` with `resume_template_id` and `cover_letter_template_id` attributes. Keeping these Python attribute names is fine as long as ORM maps them to the exact DB column names via `Column('resumeTemplateId', ...)` and `Column('coverLetterTemplateId', ...)`.

## Implementation Steps (edits the LLM should make)

1) ORM mapping updates — file: `app/models/theme.py`
- Keep Python attribute names in snake_case for consistency in the codebase, but map to camelCase DB columns explicitly:
  - Map `resume_template_id` → Column name `resumeTemplateId`, add ForeignKey("themes.id", ondelete='RESTRICT', onupdate='CASCADE').
  - Map `cover_letter_template_id` → Column name `coverLetterTemplateId`, same FK options.
- Add `previewImageUrl` column to `Theme` mapped to DB column name `previewImageUrl` (nullable String).
- Make `Theme.name` unique at the ORM level (unique=True) to mirror DB.
- Add `__table_args__` for `ThemePackage`:
  - UniqueConstraint('resumeTemplateId', 'coverLetterTemplateId', name='uq_resume_cover_pair')
  - Index('idx_resume_template', 'resumeTemplateId')
  - Index('idx_cover_letter_template', 'coverLetterTemplateId')
- Ensure `Theme.type` uses an enum compatible with DB values ('RESUME', 'COVER_LETTER'); keep existing Enum but do not attempt to create/alter DB enums.
- Prefer server-managed timestamps when possible:
  - For createdAt: server_default=func.now()
  - For updatedAt: onupdate=func.now()
  - Keep attribute names `createdAt` and `updatedAt` to match DB casing.

2) Service/CRUD review — files: `app/services/theme_service.py`, `app/crud/crud_theme.py`
- No attribute renames required if step (1) keeps Python attributes `resume_template_id` and `cover_letter_template_id` but maps them to camelCase DB columns.
- Validate before insert:
  - Confirm both referenced Theme IDs exist (to satisfy FK RESTRICT).
  - Optionally verify `Theme.type` matches intended usage (RESUME vs COVER_LETTER); not enforced here but recommended.
  - Handle uniqueness: catch duplicates for pair (`resumeTemplateId`, `coverLetterTemplateId`).

3) Pydantic schemas sanity check — file: `app/schemas/ResumeSchemas.py`
- Ensure schemas for Theme and ThemePackage remain stable (likely already correct). No changes needed unless enforcing stricter validation.
- Preserve API contracts; do not switch API payloads to camelCase.

4) Optional: raw SQL audit
- Search for any raw SQL that targets `theme_packages` and ensure it uses `resumeTemplateId` and `coverLetterTemplateId` (camelCase) in column lists.

5) Tests to add/update — files under `tests/`
- Add a focused test that:
  - Inserts two Theme records (one RESUME, one COVER_LETTER) with real IDs.
  - Creates a ThemePackage referencing those IDs via the Python attributes `resume_template_id` and `cover_letter_template_id` and verifies the row exists in DB with camelCase columns.
  - Attempts to create the same pair again and asserts a uniqueness violation is raised.
  - Optionally, tries to delete a referenced Theme and expects RESTRICT behavior (or verifies app-level prevention if DB behavior isn’t surfaced in the test DB).

## Exact Targets and Acceptance Criteria

Targets
- `app/models/theme.py` updated to map Python attrs → DB camelCase columns and to include constraints/indexes.
- No breaking changes to services or API contracts.
- Basic create/read of ThemePackage works end-to-end without `UndefinedColumn` errors.

Acceptance criteria
- Creating a ThemePackage no longer raises `UndefinedColumn` for `resume_template_id`.
- `SELECT column_name FROM information_schema.columns WHERE table_name='theme_packages'` shows camelCase column names and ORM inserts target those names.
- Duplicate pair insert raises an integrity error.
- Reading ThemePackage via CRUD returns the expected data.

## Rollout and Verification

Sequence
1) Update `app/models/theme.py` as above.
2) Run unit tests related to themes and theme packages.
3) Manually exercise POST /api/v1/themes/create (or the corresponding endpoint) to confirm 201 Created and DB row written.
4) Check logs and DB for integrity and constraints.

Manual quick checks (optional)
- Query column names for `theme_packages` to confirm camelCase.
- Attempt one end-to-end creation with known-valid Theme IDs.

## Risks and Alternatives

- Lowest risk: Adjust Python ORM to the existing Prisma schema (this plan). No DB change required.
- Alternative: Rename DB columns to snake_case via Prisma `@map` + migration (invasive; requires coordinated changes in all Prisma consumers).

## Implementation Checklist (LLM-executable)

- [ ] Edit `app/models/theme.py` to:
  - [ ] Map `resume_template_id` → Column name `resumeTemplateId`, FK to `themes.id` with ondelete RESTRICT, onupdate CASCADE.
  - [ ] Map `cover_letter_template_id` → Column name `coverLetterTemplateId`, FK to `themes.id` with ondelete RESTRICT, onupdate CASCADE.
  - [ ] Add `previewImageUrl` column on `Theme` mapped to DB `previewImageUrl` (nullable String).
  - [ ] Make `Theme.name` unique.
  - [ ] Add `__table_args__` to `ThemePackage` with UNIQUE(resumeTemplateId, coverLetterTemplateId) and helpful indexes.
  - [ ] Prefer server-side timestamps (server_default func.now, onupdate func.now) while keeping attribute names.
- [ ] Review `app/services/theme_service.py` to ensure creation path uses existing Python attribute names; add existence checks for referenced Themes.
- [ ] Audit for any raw SQL referencing `theme_packages` and fix column names to camelCase if present.
- [ ] Add/adjust tests verifying insert success, uniqueness, and basic retrieval.

Notes
- Keep Python attribute names stable in service and API layers; rely on explicit ORM column mapping to bridge to DB camelCase.
- Do not modify Prisma schema or run DB migrations for this fix.
