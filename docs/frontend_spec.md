
# Next.js Frontend Application Specification

## 1. Introduction

This document outlines the requirements for a Next.js frontend application designed to interact with the `rmcraft-backend` API. The application will provide a user interface for each of the API's endpoints, allowing for easy interaction with the backend services. The application will be for private use, and therefore does not require user authentication.

## 2. Technology Stack

- **Framework**: Next.js
- **Language**: TypeScript
- **Styling**: Tailwind CSS (or another modern CSS framework)
- **API Communication**: Axios or Fetch API

## 3. Project Structure

The application should follow a standard Next.js project structure. A suggested structure is as follows:

```
/
├── app/
│   ├── cover-letters/
│   │   ├── page.tsx
│   │   ├── create/
│   │   │   └── page.tsx
│   │   └── [id]/
│   │       └── page.tsx
│   ├── resumes/
│   │   ├── page.tsx
│   │   ├── create-from-pdf/
│   │   │   └── page.tsx
│   │   ├── strategic-analysis/
│   │   │   └── page.tsx
│   │   ├── strategy-advisor/
│   │   │   └── page.tsx
│   │   └── [id]/
│   │       └── page.tsx
│   ├── themes/
│   │   ├── page.tsx
│   │   ├── create/
│   │   │   └── page.tsx
│   │   ├── [id]/
│   │   │   └── page.tsx
│   │   └── render-pdfs/
│   │       └── page.tsx
│   └── layout.tsx
├── components/
│   ├── ui/
│   ├── forms/
│   └── navigation/
├── lib/
│   └── api.ts
├── styles/
└── ...
```

## 4. Pages and Endpoints

Each page in the application will correspond to one or more API endpoints.

### 4.1. Cover Letters

#### 4.1.1. List Cover Letters

- **Route**: `/cover-letters`
- **Endpoint**: `GET /api/v1/cover-letters/`
- **Description**: This page will display a list of all cover letters. It should include filtering and pagination options.
- **UI Components**:
    - A table displaying the cover letters with columns for key information (e.g., Title, Job, Date Created).
    - Filter controls for `resumeId`, `jobProfileId`, `from_date`, `to`, `search`, `sortBy`, and `sortOrder`.
    - Pagination controls.
    - A button to navigate to the "Create Strategic Cover Letter" page.

#### 4.1.2. Create Strategic Cover Letter

- **Route**: `/cover-letters/create`
- **Endpoint**: `POST /api/v1/cover-letters/strategic-create`
- **Description**: Generate a strategic cover letter using AI analysis. This endpoint creates a personalized cover letter by analyzing the resume and job description, identifying key matches, writing compelling content, and editing for clarity, tone, and ATS-friendliness.
- **Form Fields**:
    - `resumeId` (Text Input)
    - `jobDescriptionUrl` (Text Input)
    - `prompt` (Text Area)
    - `saveToDb` (Checkbox)
- **On Success**: Display the generated cover letter details from the `CoverLetterAPIResponse`.

#### 4.1.3. Create Manual Cover Letter

- **Route**: `/cover-letters/create-manual`
- **Endpoint**: `POST /api/v1/cover-letters/manual-create`
- **Description**: A form to create a cover letter manually without using AI agents.
- **Form Fields**:
    - `title` (Text Input)
    - `raw_text` (Text Area)
    - `resume_id` (Text Input, optional)
    - `job_profile_id` (Text Input, optional)
    - `notes` (Text Area, optional)
    - `user_id` (Text Input, optional)
- **On Success**: Display the created cover letter details from the `CoverLetterManualResponse`.

### 4.2. Resumes

#### 4.2.1. List Resumes

- **Route**: `/resumes`
- **Endpoint**: `GET /api/v1/resumes/`
- **Description**: This page will display a list of all resumes.
- **UI Components**:
    - A table displaying the resumes.
    - Pagination controls (`skip`, `limit`).
    - Buttons to navigate to the "Create from PDF", "Strategic Analysis", and "Strategy Advisor" pages.

#### 4.2.2. View Resume

- **Route**: `/resumes/[id]`
- **Endpoint**: `GET /api/v1/resumes/{resume_id}`
- **Description**: Displays the full details of a single resume.
- **UI Components**:
    - A detailed view of all the fields in the `ResumeResponse` schema.

#### 4.2.3. Create Resume from PDF

- **Route**: `/resumes/create-from-pdf`
- **Endpoint**: `POST /api/v1/resumes/create-from-pdf`
- **Description**: A form to upload a PDF and create a resume.
- **Form Fields**:
    - `file` (File Input)
    - `user_id` (Text Input, optional)
- **On Success**: Display the created resume details.

#### 4.2.4. Strategic Resume Analysis

- **Route**: `/resumes/strategic-analysis`
- **Endpoint**: `POST /api/v1/resumes/strategic-analysis`
- **Description**: Analyze a resume strategically against a job description using AI agents. This endpoint uses Google ADK agents to parse and analyze the resume content, extract relevant information from the job description URL, match relevant experience, skills, and projects, and provide strategic recommendations for resume optimization.
- **Form Fields**:
    - `resume_id` (Text Input)
    - `job_description_url` (Text Input)
    - `theme_id` (Text Input, optional)
- **On Success**: Display the analysis results from the `StrategicResumeResponse`.

#### 4.2.5. Strategy Advisor

- **Route**: `/resumes/strategy-advisor`
- **Endpoint**: `POST /api/v1/resumes/strategy-advisor`
- **Description**: This endpoint develops a full strategy for creating a strategic resume and cover letter. It uses the strategy advisor in isolation to parse and analyze the resume content, extract relevant information from the job description URL, and return plain text strategic analysis.
- **Form Fields**:
    - `resume_id` (Text Input)
    - `job_description_url` (Text Input)
- **On Success**: Display the strategic advice from the `StrategicResumeResponse`.

### 4.3. Themes

#### 4.3.1. List Themes

- **Route**: `/themes`
- **Endpoint**: `GET /api/v1/themes/`
- **Description**: This page will display a list of all theme packages.
- **UI Components**:
    - A grid or list displaying the theme packages.
    - A button to navigate to the "Create Theme" page.

#### 4.3.2. Create Theme

- **Route**: `/themes/create`
- **Endpoint**: `POST /api/v1/themes/create`
- **Description**: Agentically generates and saves a new resume and cover letter theme based on a text prompt and an inspiration image.
- **Form Fields**:
    - `design_prompt` (Text Area)
    - `inspiration_image` (File Input)
    - `user_id` (Text Input, optional)
- **On Success**: Display the created theme details.

#### 4.3.3. View Theme

- **Route**: `/themes/[id]`
- **Endpoint**: `GET /api/v1/themes/{theme_package_id}`
- **Description**: Displays the details of a specific theme package.
- **UI Components**:
    - A view of the theme package, including the resume and cover letter templates.

#### 4.3.4. Render PDFs

- **Route**: `/themes/render-pdfs`
- **Endpoint**: `POST /api/v1/themes/render-pdfs`
- **Description**: Generate PDFs for a stored resume + cover letter using a ThemePackage. Returns local file paths and (optionally) uploaded Cloudinary URLs.
- **Form Fields**:
    - `theme_package_id` (Text Input)
    - `resume_id` (Text Input)
    - `cover_letter_id` (Text Input)
    - `upload` (Checkbox)
- **On Success**: Display the paths to the generated PDFs.

## 5. API Integration

A dedicated module (e.g., `lib/api.ts`) should be created to handle all API requests. This module will contain functions that correspond to each endpoint, making it easy to manage API calls and handle responses and errors centrally.

## 6. Styling and UI

The application should have a clean and modern user interface. The use of a component library like Shadcn/UI (which is based on Tailwind CSS) is recommended to ensure a consistent and professional look and feel.
