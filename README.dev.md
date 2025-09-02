Developer setup quickstart

1. Create and activate a virtualenv using Poetry:

```bash
cd /Users/berato/Sites/rmcraft-backend
poetry install
poetry shell
```

2. If you prefer a local `.venv` inside the project (recommended for VS Code):

```bash
poetry config virtualenvs.in-project true
poetry install
```

3. In VS Code, pick the interpreter at `.venv/bin/python` (the workspace settings include this path).

4. If the editor still shows unresolved imports, run:

```bash
# ensure poetry created the .venv and dependencies are installed
poetry install
# then reload the VS Code window (Developer: Reload Window)
```

## API Usage

### Strategic Resume Analysis Endpoint

The `/api/v1/resumes/strategic-analysis` endpoint analyzes a resume against a job description and generates a custom PDF design.

**Endpoint:** `POST /api/v1/resumes/strategic-analysis`

**Content-Type:** `multipart/form-data`

**Parameters:**
- `resume_id` (string, required): The ID of the resume to analyze
- `job_description_url` (string, required): URL of the job description to analyze against
- `design_prompt` (string, required): Description of the desired resume design
- `inspiration_image` (file, required): Image file to use as design inspiration

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/resumes/strategic-analysis" \
  -F "resume_id=cme3py2tu0003fbrzfxt8wuum" \
  -F "job_description_url=https://example.com/job-posting" \
  -F "design_prompt=A clean designer resume with strong, bold fonts" \
  -F "inspiration_image=@/path/to/your/image.jpg"
```

**Example using Python requests:**
```python
import requests

url = "http://localhost:8000/api/v1/resumes/strategic-analysis"
form_data = {
    "resume_id": "cme3py2tu0003fbrzfxt8wuum",
    "job_description_url": "https://example.com/job-posting",
    "design_prompt": "A clean designer resume with strong, bold fonts"
}
files = {
    "inspiration_image": ("image.jpg", open("path/to/image.jpg", "rb"), "image/jpeg")
}

response = requests.post(url, data=form_data, files=files)
```

**Response:**
```json
{
  "status": 200,
  "message": "Strategic analysis and PDF generation completed successfully",
  "data": {
    "pdf_url": "https://cloudinary.com/...",
    "analysis": {...}
  }
}
```

### Cover Letters Endpoints

#### List Cover Letters

The `/api/v1/cover-letters/` endpoint provides a paginated, filterable list of cover letters.

**Endpoint:** `GET /api/v1/cover-letters/`

**Query Parameters:**
- `page` (integer, optional): Page number (default: 1)
- `perPage` (integer, optional): Items per page (default: 20, max: 100)
- `resumeId` (string, optional): Filter by resume ID
- `jobProfileId` (string, optional): Filter by job profile ID
- `from_date` (string, optional): Filter by created date >= from_date (ISO format)
- `to` (string, optional): Filter by created date <= to (ISO format)
- `search` (string, optional): Free text search in title and content
- `sortBy` (string, optional): Sort field (createdAt, wordCount, atsScore) (default: createdAt)
- `sortOrder` (string, optional): Sort order (asc, desc) (default: desc)
- `include` (string, optional): Comma-separated list of fields to include (e.g., "finalContent")

**Example using curl:**
```bash
curl -G "http://localhost:8000/api/v1/cover-letters/" \
  --data-urlencode "page=1" \
  --data-urlencode "perPage=20" \
  --data-urlencode "resumeId=test-resume-123" \
  --data-urlencode "search=engineer" \
  --data-urlencode "sortBy=createdAt" \
  --data-urlencode "sortOrder=desc"
```

**Response:**
```json
{
  "status": 200,
  "message": "Cover letters retrieved successfully",
  "data": {
    "items": [
      {
        "id": "cover-letter-uuid",
        "title": "Strategic Cover Letter",
        "jobDetails": {
          "title": "Software Developer",
          "company": "Tech Corp",
          "url": "https://example.com/job"
        },
        "resumeId": "resume-uuid",
        "jobProfileId": null,
        "createdAt": "2024-01-01T00:00:00",
        "updatedAt": "2024-01-01T00:00:00",
        "wordCount": 320,
        "atsScore": 8
      }
    ],
    "meta": {
      "page": 1,
      "perPage": 20,
      "total": 1,
      "totalPages": 1
    }
  }
}
```

#### Create Strategic Cover Letter

The `/api/v1/cover-letters/strategic-create` endpoint generates a strategic cover letter using AI analysis.

**Endpoint:** `POST /api/v1/cover-letters/strategic-create`

**Content-Type:** `application/json`

**Parameters:**
- `resumeId` (string, required): The ID of the resume to use
- `jobDescriptionUrl` (string, required): URL of the job description
- `prompt` (string, optional): Custom prompt for the AI
- `saveToDb` (boolean, optional): Whether to save to database (default: true)

**Example using curl:**
```bash
curl -X POST "http://localhost:8000/api/v1/cover-letters/strategic-create" \
  -H "Content-Type: application/json" \
  -d '{
    "resumeId": "test-resume-123",
    "jobDescriptionUrl": "https://example.com/job",
    "prompt": "Make it enthusiastic",
    "saveToDb": true
  }'
```

**Response:**
```json
{
  "status": 201,
  "message": "Strategic cover letter generated successfully",
  "data": {
    "title": "Strategic Cover Letter",
    "jobDetails": {
      "title": "Software Developer",
      "company": "Tech Corp",
      "url": "https://example.com/job"
    },
    "openingParagraph": "Dear Hiring Manager,",
    "bodyParagraphs": ["I am excited to apply...", "My experience includes..."],
    "closingParagraph": "Thank you for your consideration.",
    "tone": "professional",
    "finalContent": "Full cover letter content...",
    "resumeId": "test-resume-123",
    "createdAt": "2024-01-01T00:00:00",
    "updatedAt": "2024-01-01T00:00:00",
    "wordCount": 320,
    "atsScore": 8,
    "coverLetterId": "cover-letter-uuid"
  }
}
```
