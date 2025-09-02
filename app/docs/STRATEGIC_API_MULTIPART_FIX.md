# Fixing the Strategic Resume Endpoint: multipart/form-data + OpenAPI/Swagger

This document explains the root cause of the 422 errors and Swagger showing a single JSON box for the `/api/v1/resumes/strategic-analysis` endpoint, and gives a full, explicit plan (server + client + verification) an LLM or engineer can follow to fix the problem so Swagger presents separate form fields plus a file chooser.

## Goal
- Accept text inputs (resume_id, job_description_url, design_prompt) and an uploaded image (`inspiration_image`) in one request.
- Ensure FastAPI generates an OpenAPI/Swagger UI that shows separate input fields for each text value and a file chooser for the binary.
- Preserve Pydantic validation where useful.

## Problem summary (short)
- JSON body (application/json) and file uploads (multipart/form-data) are different HTTP content types. FastAPI cannot parse both simultaneously into a Pydantic body model.
- If the route signature still includes a Pydantic Body parameter, FastAPI will describe the request body as JSON in the OpenAPI schema, so Swagger renders a JSON editor rather than separate form fields.
- Swagger (the UI) is driven entirely from FastAPI's OpenAPI schema. To get Swagger to show form fields + file, the route signature must declare `Form(...)` and `File(...)` parameters.

## Requirements checklist (for a proper fix)
- [ ] Route signature uses `Form(...)` for each text input and `File(...)` for the file input
- [ ] Remove Pydantic Body parameters from the function signature (or accept a JSON string form field and parse it)
- [ ] Optionally validate with Pydantic by constructing a model from the `Form` values inside the function (or via a dependency)
- [ ] Restart server and confirm `/openapi.json` shows `multipart/form-data` with properties for each field
- [ ] Clear browser cache and verify `/docs` shows separate fields + file chooser

## Recommended server-side changes (conceptual)
Pick one of these two approaches.

### Option A — Explicit Form + File (recommended)
- Change function signature to use Form and File parameters. Example:

```py
from fastapi import Form, File, UploadFile

@router.post("/strategic-analysis", response_model=StrategicResumeResponse)
async def strategic_resume_analysis(
    resume_id: str = Form(...),
    job_description_url: str = Form(...),
    design_prompt: str = Form(...),
    inspiration_image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # Optionally create a Pydantic model to validate these values:
    data = StrategicResumeRequest(
        resume_id=resume_id,
        job_description_url=job_description_url,
        design_prompt=design_prompt,
    )
    # ...handle image and call agent
```

Why this works:
- Declaring `Form(...)` parameters makes FastAPI set the OpenAPI requestBody `content` to `multipart/form-data` with separate properties. Swagger will render separate text fields and a file chooser.
- You still get Pydantic validation by constructing the Pydantic model inside the handler (so you get type coercion and error messaging if fields are invalid).

### Option B — Single JSON part + file (fallback UX)
If you can't change clients to send separate form fields, the server can accept a single form field that contains JSON, plus the binary file:

```py
from fastapi import Form, File, UploadFile
import json

@router.post("/strategic-analysis")
async def strategic_resume_analysis(
    request_json: str = Form(...),
    inspiration_image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    payload = json.loads(request_json)
    data = StrategicResumeRequest(**payload)
    # ...handle image and call agent
```

Tradeoffs:
- Swagger will render a single text area named `request_json` + file chooser. Not as ergonomic as separate fields, but works when clients send a single JSON blob.

## How to preserve Pydantic validation while keeping good OpenAPI docs
- Use `Form(...)` params in the signature for doc generation.
- Inside the handler, construct the Pydantic model (e.g. `StrategicResumeRequest(...)`) from the `Form` values. If the model raises validation errors, return 400 with details.
- Alternatively, implement a dependency that accepts `Form` params and returns a validated model (helps keep the handler body clean).

Dependency pattern example (clean validation + docs):

```py
from fastapi import Depends

def strategic_request_dependency(
    resume_id: str = Form(...),
    job_description_url: str = Form(...),
    design_prompt: str = Form(...),
):
    return StrategicResumeRequest(
        resume_id=resume_id,
        job_description_url=job_description_url,
        design_prompt=design_prompt,
    )

@router.post("/strategic-analysis")
async def endpoint(
    request: StrategicResumeRequest = Depends(strategic_request_dependency),
    inspiration_image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    # request is already validated Pydantic model
```

## Client examples (multipart/form-data) — use these in tests and docs
- curl

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/resumes/strategic-analysis" \
  -F "resume_id=cme3py2tu0003fbrzfxt8wuum" \
  -F "job_description_url=https://example.com/job-posting" \
  -F "design_prompt=A clean designer resume" \
  -F "inspiration_image=@/path/to/image.jpg"
```

- Python requests

```py
import requests

url = "http://127.0.0.1:8000/api/v1/resumes/strategic-analysis"
form_data = {
    "resume_id": "cme3py2tu0003fbrzfxt8wuum",
    "job_description_url": "https://example.com/job-posting",
    "design_prompt": "A clean designer resume"
}
files = {"inspiration_image": ("image.jpg", open("/path/to/image.jpg", "rb"), "image/jpeg")}
resp = requests.post(url, data=form_data, files=files)
print(resp.status_code, resp.text)
```

## Verifying the OpenAPI schema and Swagger UI
1. Start (or restart) the server.
2. Open `http://127.0.0.1:8000/openapi.json` and find the path `/api/v1/resumes/strategic-analysis`.
3. Confirm `requestBody.content` contains `multipart/form-data` and `schema.properties` includes `resume_id`, `job_description_url`, `design_prompt` (type: string) and `inspiration_image` (type: string, format: binary).
4. Open `http://127.0.0.1:8000/docs` — you should now see separate form inputs and a file picker.
5. Use the Swagger "Try it out" to send a sample request with a local image file.

If the OpenAPI still shows `application/json`, find any remaining function parameter typed to a Pydantic model or using `Body(...)` — this must be converted to `Form(...)` or removed from the signature.

## Troubleshooting checklist
- If Swagger still shows a single JSON editor:
  - Search code for any parameter in that route that is a Pydantic model. Remove it from the function signature.
  - Ensure `inspiration_image` is `UploadFile = File(...)` and text fields are `Form(...)`.
  - Restart the server, clear browser cache, reload `/docs`.
- If multipart requests succeed via curl but not Swagger UI:
  - Make sure Swagger UI can access local files — some browser restrictions require user file selection.
- If you need to accept JSON body + file simultaneously (not recommended):
  - Accept a form `request_json` string and parse it server-side (Option B above).

## Tests to add / update
- Update integration tests sending requests to the endpoint to use `data=` + `files=` instead of `json=`.
- Add a unit test for the dependency that constructs the Pydantic model from `Form` values (if you implemented the dependency approach).

## Example small migration plan (concrete steps for a committer/LLM to apply)
- [ ] Edit `app/api/v1/endpoints/resumes.py`: change endpoint signature to accept `Form(...)` for text fields and `File(...)` for `inspiration_image`.
- [ ] Remove `StrategicResumeRequest` from function signature; optionally keep the Pydantic class for internal validation.
- [ ] Inside the handler (or dependency) instantiate `StrategicResumeRequest(...)` for validation.
- [ ] Update tests: `test_strategic_endpoint.py` and `test_strategic_comprehensive.py` to use multipart requests.
- [ ] Restart the app, open `/openapi.json`, and confirm `multipart/form-data` is present.
- [ ] Verify `/docs` UI; try request with image.

## Notes for an LLM operator
- The LLM should edit the function signature only — avoid changing other business logic.
- If asked to also modify tests, change `requests.post(..., json=...)` to `requests.post(..., data=..., files=...)` in the repo tests and example scripts.
- The code changes required are small and safe: they only affect how FastAPI parses the incoming request and how the OpenAPI schema is generated.

---

If you want, I can now:
- Create a pull request with the minimal code change to `app/api/v1/endpoints/resumes.py` and update the two tests, or
- Just implement the dependency pattern for validation and run the tests locally.

Pick one and I'll proceed. 
