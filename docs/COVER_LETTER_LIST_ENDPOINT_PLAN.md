## Cover Letters - List Endpoint Implementation Plan

Goal
----

Add a safe, paginated, filterable HTTP endpoint to list persisted cover letters. This document is a complete implementation plan intended for an LLM agent or developer to implement the feature end-to-end without further clarification. It mirrors the style and conventions already used in the project (SQLAlchemy models in `app/models`, service layer in `app/services`, endpoints in `app/api/v1/endpoints`).

Requirements checklist
---------------------

- [ ] Provide a read-only endpoint to list cover letters: `GET /api/v1/cover-letters` (or similar).
- [ ] Support pagination (page/perPage) with sensible defaults and limits.
- [ ] Support filtering by `resumeId`, `jobProfileId`, date range (`createdAt`), and free-text search across `title` and `finalContent` (basic LIKE search or full-text where available).
- [ ] Support sorting (by `createdAt`, `wordCount`, `atsScore`) and sort direction.
- [ ] Return a compact summary object per cover letter (no huge fields by default) with an option to include full content via `?include=finalContent`.
- [ ] Enforce authorization: users can only list cover letters they own (resume ownership) unless requester is an admin.
- [ ] Service-layer implementation with DB session handling and performance-conscious queries.
- [ ] Add indexes recommended for filters and sorts: `resumeId`, `jobProfileId`, `createdAt`, and optionally `wordCount`/`atsScore` if sorts are heavy.
- [ ] Add unit and endpoint tests, and at least one integration test covering pagination, filters, and auth.
- [ ] Add logging, metrics, and defensive limits (max perPage, search length limit).
- [ ] Keep API backward-compatible and documented in OpenAPI/pydantic models.

High level design
-----------------

1. API endpoint: `GET /api/v1/cover-letters`
   - Query parameters:
     - `page` (int, default 1)
     - `perPage` (int, default 20, max 100)
     - `resumeId` (string, optional)
     - `jobProfileId` (string, optional)
     - `from` (ISO datetime string, optional) — filter createdAt >= from
     - `to` (ISO datetime string, optional) — filter createdAt <= to
     - `search` (string, optional) — free text search across `title` and `finalContent`
     - `sortBy` (string, optional) — one of `createdAt`, `wordCount`, `atsScore` (default `createdAt`)
     - `sortOrder` (string, optional) — `asc` or `desc` (default `desc`)
     - `include` (string or comma list) — optional fields to include in the response, e.g. `include=finalContent`.

2. Response shape (JSON envelope):

```json
{
  "status": 200,
  "message": "List of cover letters",
  "data": {
    "items": [
      {
        "id": "<uuid>",
        "title": "Strategic Cover Letter",
        "jobDetails": {"title": "...", "company": "...", "url": "..."},
        "resumeId": "<resume-id>",
        "jobProfileId": "<job-profile-id> or null",
        "createdAt": "<iso-datetime>",
        "updatedAt": "<iso-datetime>",
        "wordCount": 320,
        "atsScore": 8,
        // optionally included if requested
        "finalContent": "..."
      }
    ],
    "meta": {
      "page": 1,
      "perPage": 20,
      "total": 123,
      "totalPages": 7
    }
  }
}
```

3. Authorization
   - The service will receive the current user's identity (e.g., from request context or dependency). Only return cover letters that the user is allowed to see.
   - Rule: a cover letter is visible if the user owns the resume referenced by `resumeId`, or the user has an `admin` role.
   - Implementation note: reuse existing auth dependency patterns used by resume endpoints.

4. Service layer contract
   - New function in `app/services/cover_letter_service.py`:
     - `def list_cover_letters(db: Session, *, page: int = 1, per_page: int = 20, filters: Dict[str, Any] = None, search: Optional[str] = None, sort_by: str = 'createdAt', sort_order: str = 'desc', include: Optional[List[str]] = None, current_user: Optional[UserModel] = None) -> Dict[str, Any]`
     - Inputs: DB session, pagination, filters, search, sorting, include list, and current user for authorization
     - Output: `{ items: List[dict], meta: { page, perPage, total, totalPages } }`
   - The function performs:
     - Validate pagination and bounds
     - Build a SQLAlchemy query for `CoverLetter`
     - Apply ownership filter for the current user unless admin
     - Apply provided filters and date ranges
     - Apply free-text search using `ILIKE`/`LIKE` or DB full-text (optional)
     - Count total rows efficiently (use window functions if needed or a separate count query)
     - Apply ordering and limit/offset
     - Load only summary columns by default (`id`, `title`, `jobDetails`, `resumeId`, `jobProfileId`, `createdAt`, `updatedAt`, `wordCount`, `atsScore`)
     - If `finalContent` requested via `include`, load that column too
     - Return results as dicts (or pydantic models)

5. Database and indexes
   - Ensure the `cover_letters` table has the indexes used for queries:
     - `idx_cover_letters_resumeId` (resumeId)
     - `idx_cover_letters_jobProfileId` (jobProfileId)
     - Consider adding index on `createdAt` if heavy range queries
     - If `search` will be used frequently and DB supports it (Postgres), implement a `tsvector` column + GIN index for full-text search on `title` and `finalContent`.

6. Pagination strategy and limits
   - Default `perPage` = 20, max `perPage` = 100
   - Use offset/limit for simplicity; offer cursor-based pagination later for large datasets

7. Input validation and defensive limits
   - Reject `perPage` > 100 with 400
   - Reject extremely long `search` strings (> 1024 chars)
   - Validate date formats and return 422 for invalid

8. Logging and metrics
   - Log queries at debug level with filters and page info (no PII)
   - Log request summary: user id, filters, page/perPage, items returned
   - Track metrics: request count, average latency, cache hit rate if used

9. Tests
   - Unit tests for `list_cover_letters()` service:
     - test_list_default_pagination
     - test_list_filter_by_resume
     - test_list_filter_by_jobProfile
     - test_date_range_filter
     - test_search_returns_matching
     - test_include_finalContent
     - test_auth_filters (user only sees their resumes)

   - Endpoint tests (fastapi test client):
     - list endpoint returns expected envelope and meta
     - pagination returns correct counts and pages
     - include parameter returns `finalContent` only when requested
     - unauthorized user gets 403 when trying to access others' cover letters

   - Integration test:
     - Create multiple cover letters in test DB, call endpoint with filters and verify results end-to-end

10. OpenAPI / Pydantic models
    - Request: query params described earlier
    - Response: create `CoverLetterSummary` pydantic model and `CoverLetterListResponse` envelope matching the JSON above. Add these to `app/api/v1/endpoints/cover_letters.py` file when implementing.

11. Monitoring and alerting
    - Add an error log and a monitoring event when DB queries fail or when page/perPage misuse occurs
    - Add metric for average listing latency and requests per second

12. Rate limiting and caching
    - Consider caching responses for identical queries for short TTL (30s) for public data or admin dashboards
    - Rate-limit listing endpoints for non-admin users to prevent abuse

13. Rollout and backwards compatibility
    - This is an additive read-only endpoint; no breaking changes are expected
    - Ensure default response shape matches existing clients (if any); keep previous endpoint behavior if it exists

Edge cases & operational notes
--------------------------------

- Large `finalContent` fields: ensure the endpoint does not eagerly transfer full contents unless requested. By default return summaries.
- Count query performance: on very large tables, count queries may be expensive; consider cached approximate counts or window functions depending on DB.
- Search accuracy: start with simple ILIKE/LIKE; move to Postgres full-text search (tsvector + GIN index) if usage grows.
- Timezone handling: always store and return ISO8601 UTC timestamps.

Acceptance criteria
-------------------

- [ ] `GET /api/v1/cover-letters` returns paginated list of cover letter summaries.
- [ ] Filters (`resumeId`, `jobProfileId`, date range) return expected subset.
- [ ] Sorting and search work as specified.
- [ ] Authorization enforced: users only see their cover letters (or admin sees all).
- [ ] `include=finalContent` returns full letter content only when requested.
- [ ] Unit and endpoint tests exist and pass locally against test DB.

Implementation hints for an LLM agent
-----------------------------------

- Follow existing project patterns: models in `app/models`, services in `app/services`, router endpoints in `app/api/v1/endpoints`.
- Reuse `SessionLocal` from `app/db/session.py` and existing auth dependencies used in the resume endpoints to obtain `current_user`.
- Prefer returning pydantic models from endpoints for consistent validation and OpenAPI docs.
- Keep the SQLAlchemy queries readable and testable; prefer composable filters.

Deliverables
------------

- New or updated docs file (this file)
- Implementation tasks for code (service, endpoint, tests) — no code changes here per instruction
- Suggested migration already exists (table), no new migration needed strictly for listing

Example curl (for implementer/testing):

```bash
curl -G "http://localhost:8000/api/v1/cover-letters" \
  --data-urlencode "page=1" \
  --data-urlencode "perPage=20" \
  --data-urlencode "resumeId=test-resume-123" \
  --data-urlencode "search=engineer" \
  -H "Authorization: Bearer <token>"
```

Notes
-----

This plan intentionally keeps the implementation flexible for future improvements such as cursor pagination, advanced search, or a dedicated read-model for analytics. Start with a simple, well-tested implementation that favours clarity and safety.

---

Document created for implementers and LLM agents to pick up and implement in the codebase.
