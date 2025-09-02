# Diagnostic Report: `strategic-analysis` Endpoint Error

## 1. Symptom

When sending a request to the `/api/v1/resumes/strategic-analysi# Simply omit the inspiration_image part
curl -X POST "http://localhost:8000/api/v1/resumes/strategic-analysis" 
  -F "resume_id=some_id" 
  -F "job_description_url=http://example.com" 
  -F "design_prompt=A cool design"dpoint, the server returns a `422 Unprocessable Entity` error with the following detail:

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": [
        "body",
        "inspiration_image"
      ],
      "msg": "Value error, Expected UploadFile, received: <class 'str'>",
      "input": "",
      "ctx": {
        "error": {}
      }
    }
  ]
}
```

This error clearly indicates that the `inspiration_image` field was expected to be a file upload (`UploadFile`), but the server received a string (`str`) instead.

## 2. Root Cause Analysis

The endpoint is defined in `app/api/v1/endpoints/resumes.py` as follows:

```python
@router.post("/strategic-analysis", response_model=StrategicResumeResponse)
async def strategic_resume_analysis(
    resume_id: str = Form(...),
    job_description_url: str = Form(...),
    design_prompt: str = Form(...),
    inspiration_image: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db)
):
    # ... endpoint logic
```

The use of `Form(...)` and `File(...)` decorators explicitly tells FastAPI to expect a request with the `Content-Type` of `multipart/form-data`. This format is necessary to handle a mix of regular form fields (like `resume_id`) and file uploads (like `inspiration_image`).

The error occurs because the client's request, while likely targeting the correct endpoint, is not formatting the `inspiration_image` part as a file. Instead, it is being sent as a simple string value (in this case, an empty string `""`), which FastAPI cannot parse into an `UploadFile` object.

## 3. Potential Causes

There are several common reasons why a client might send this data incorrectly:

### Cause A: Sending `application/json` instead of `multipart/form-data`
The client might be sending a JSON payload. A JSON request to this endpoint would fail because the server is configured for form data, not a JSON body.

**Incorrect JSON Request Example:**
```json
// POST /api/v1/resumes/strategic-analysis
// Content-Type: application/json

{
  "resume_id": "some_id",
  "job_description_url": "http://example.com",
  "design_prompt": "A cool design",
  "inspiration_image": "" // This string causes the error
}
```

### Cause B: Incorrect `multipart/form-data` Request
Even when using `multipart/form-data`, the request can be malformed. This often happens when using API clients like Postman or Insomnia, or with `curl`.

- **Postman/Insomnia:** The user might have set the type for the `inspiration_image` key to "Text" instead of "File".
- **`curl`:** The user might have forgotten the `@` prefix for the file path, which tells `curl` to treat the string as a file path to upload.

**Incorrect `curl` Example:**
```bash
# This sends the literal string "/path/to/image.jpg" instead of the file's contents
curl -X POST ... -F "inspiration_image=/path/to/image.jpg"
```

### Cause C: Using FastAPI's Swagger UI Incorrectly
When using the auto-generated docs at `/docs`, the `inspiration_image` field is an optional file upload. If the user executes the request without selecting a file, some browsers may still include the form part but with an empty value, which gets interpreted as an empty string on the server side.

## 4. Recommended Solution & Correct Usage

The solution is to ensure the client always sends a correctly formatted `multipart/form-data` request. The `inspiration_image` part should either contain valid file data or be omitted entirely if no file is being uploaded.

### For Python `requests`
The `example_strategic_call.py` script demonstrates the correct approach. Use the `data` parameter for text fields and the `files` parameter for file uploads.

**Correct `requests` Example:**
```python
import requests

# The URL of the endpoint
url = "http://localhost:8000/api/v1/resumes/strategic-analysis"

# Form data for text fields
form_data = {
    "resume_id": "cme3py2tu0003fbrzfxt8wuum",
    "job_description_url": "https://example.com/job",
    "design_prompt": "A clean and modern design."
}

# File to upload. Ensure the path is correct.
# The key 'inspiration_image' must match the parameter name in the endpoint.
files = {
    "inspiration_image": ("resume_inspiration.jpg", open("path/to/your/image.jpg", "rb"), "image/jpeg")
}

# If no file is being sent, use an empty dictionary or None for the files parameter
# files = None

try:
    response = requests.post(url, data=form_data, files=files)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

except FileNotFoundError:
    print("❌ Error: The image file was not found. Please check the path.")
except requests.exceptions.ConnectionError:
    print("❌ Error: Could not connect to the server.")
```

### For `curl`
Use the `-F` flag for each form field. For the file, prefix the path with `@`.

**Correct `curl` Example (with file):**
```bash
curl -X POST "http://localhost:8000/api/v1/resumes/strategic-analysis" \
  -F "resume_id=some_id" \
  -F "job_description_url=http://example.com" \
  -F "design_prompt=A cool design" \
  -F "inspiration_image=@/path/to/your/image.jpg"
```

**Correct `curl` Example (without file):**
```bash
# Simply omit the inspiration_image part
curl -X POST "http://localhost:8000/api/v1/resumes/strategic-analysis" \
  -F "resume_id=some_id" \
  -F "job_description_url=http://example.com" \
  -F "design_prompt=A cool design"
```

## 5. Proposed Long-Term Solutions

Based on further analysis, the `inspiration_image` issue is a symptom of a larger architectural problem. The strategic analysis endpoint is trying to do too much: perform a complex AI-driven analysis AND handle bespoke design generation in a single, synchronous request. This leads to fragility and a poor user experience.

The following is a plan to refactor the feature into a more robust and maintainable state.

### 5.1. Immediate Fix: Handling Empty Image Uploads

To make the endpoint immediately usable, especially from the Swagger UI, the code should gracefully handle cases where `inspiration_image` is sent but is empty.

**Action for LLM:**
In `app/api/v1/endpoints/resumes.py`, modify the `strategic_resume_analysis` endpoint to check if the `inspiration_image` is present but empty. An empty `UploadFile` might have a `filename` that is an empty string.

**Example Logic:**
```python
# Inside strategic_resume_analysis endpoint

inspiration_image_data = None
inspiration_image_mime_type = None

# Add a check to see if the file object exists and has a filename
if inspiration_image and inspiration_image.filename:
    try:
        # ... existing code to read file ...
        inspiration_image_data = await inspiration_image.read()
        inspiration_image_mime_type = inspiration_image.content_type
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading uploaded image: {str(e)}")
```
This prevents the `Value error, Expected UploadFile, received: <class 'str'>` when no file is selected in a form submission from a browser.

### 5.2. Refactoring Plan: Decouple Strategic Analysis from Design Generation

The core of the problem is that the design/theming work is tightly coupled with the strategic analysis. This should be separated. The strategic analysis agent should only be responsible for the analysis, not for generating a PDF.

**Action Plan for LLM:**

**Step 1: Modify the Endpoint Signature**
In `app/api/v1/endpoints/resumes.py`, update the `strategic_resume_analysis` function signature:
- **Remove** `design_prompt: str = Form(...)`.
- **Remove** `inspiration_image: Optional[UploadFile] = File(None)`.
- **Add** an optional `theme_id: Optional[str] = Form(None)`.

**New Signature:**
```python
@router.post("/strategic-analysis", response_model=StrategicResumeResponse)
async def strategic_resume_analysis(
    resume_id: str = Form(...),
    job_description_url: str = Form(...),
    theme_id: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # ...
```

**Step 2: Simplify the Endpoint Logic**
Inside the endpoint, remove all code related to reading the `inspiration_image`.

**Step 3: Update the Agent Call**
Modify the call to `strategic_resume_agent` to pass only the relevant information. The design-related parameters should be removed.

**New Agent Call:**
```python
# Inside strategic_resume_analysis endpoint

result = await asyncio.wait_for(
    strategic_resume_agent(
        resume_id=resume_id,
        job_description_url=job_description_url,
    ),
    timeout=65.0,
)
```

**Step 4: Refactor the `strategic_resume_agent`**
This is the most critical part. The agent located at `app/agents/resume/strategic/strategic_resume_agent.py` must be refactored:
- **Remove all tools and logic related to design and PDF generation.** This includes any prompts that instruct the agent to think about design, use `design_prompt`, or process an `inspiration_image`.
- **The agent's final output should be the structured strategic analysis data (e.g., a JSON object containing strengths, weaknesses, and recommendations), not a URL to a PDF.** The agent's purpose is analysis, not presentation.

**Step 5: Handle PDF Generation Separately (Post-Analysis)**
After the agent returns the analysis, the endpoint can then optionally generate a PDF if a `theme_id` was provided.
- If `theme_id` is present, use the returned analysis data and the original resume data to populate a template.
- A separate service, potentially using the existing `pdf_generator.py` tool, should be called to create the PDF. This service would take the resume data and `theme_id` as input.

**Example Post-Analysis Flow:**
```python
# Inside strategic_resume_analysis, after the agent call returns `result`

analysis_data = result # This is the JSON output from the agent

pdf_url = None
if theme_id:
    # You will likely need to fetch the full resume data here
    resume_data = crud_resume.get_resume(db, resume_id)
    
    # Call a separate PDF generation service
    # This is a conceptual function; implementation will be needed
    pdf_url = generate_themed_resume_pdf(resume_data, theme_id, analysis_data)

# Update the final response
return {
    "status": 200,
    "message": "Strategic analysis completed successfully.",
    "data": {
        "analysis": analysis_data,
        "pdf_url": pdf_url # This will be None if no theme_id was provided
    }
}
```

By following this plan, the `strategic-analysis` feature will be more robust, modular, and easier to maintain. The core value (the AI analysis) is separated from the presentation (the PDF design), resolving the current bug and improving the overall architecture.
