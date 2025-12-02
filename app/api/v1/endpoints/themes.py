from bson import ObjectId
from fastapi import APIRouter, Body, UploadFile, File, Form, status, HTTPException
from app.features.theme_generator import create_and_save_theme
from app.schemas.ResumeSchemas import ThemePackage, ResumeResponse  # Import actual schemas
from app.schemas.CoverLetterSchemas import CoverLetterFull
from typing import List, Optional
from app.crud import crud_theme
from app.services.designer_pdf import create_designed_pdfs, get_example_theme
from app.schemas.theme import ThemeSchema, ThemeTemplate, ThemePackageWithTemplates
from app.schemas.theme_documents import ThemeDoc, ThemePackageDoc
from app.schemas.triage_schemas import ThemeTriageResponse
from app.workflows.theme_triage_workflow import execute_theme_triage_workflow
import uuid

router = APIRouter(prefix="/themes", tags=["themes"])

@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=ThemePackageDoc)
async def create_theme_endpoint(
    design_prompt: str = Body(..., embed=True),
    inspiration_image: UploadFile = File(...),
    user_id: Optional[str] = Body(None, embed=True),
):
    """
    Agentically generates and saves a new resume and cover letter theme
    based on a text prompt and an inspiration image.
    """
    image_data = await inspiration_image.read()
    image_mime_type = inspiration_image.content_type
    
    # If user_id is not provided, generate a new one.
    effective_user_id = user_id if user_id else str(uuid.uuid4())

    # The orchestrator runs the full workflow and returns a saved ThemePackage
    saved_theme = await create_and_save_theme(
        design_prompt=design_prompt,
        image_data=image_data,
        image_mime_type=image_mime_type,
        user_id=effective_user_id,
    )
    
    return saved_theme

@router.get("/", response_model=List[ThemePackageDoc])
async def read_themes(skip: int = 0, limit: int = 100):
    """
    Retrieve a list of theme packages.
    """
    themes = await crud_theme.get_theme_packages(skip=skip, limit=limit)
    return themes

@router.get("/{theme_package_id}", response_model=ThemePackageWithTemplates)
async def read_theme_package(theme_package_id: str):
    """
    Retrieve a specific theme package by ID.
    """
    package_doc = await crud_theme.get_theme_package_by_id(theme_package_id)
    if package_doc is None:
        raise HTTPException(status_code=404, detail="Theme package not found")

    resume_theme_doc = await crud_theme.get_theme_by_id(package_doc.resumeTemplateId)
    cover_letter_theme_doc = await crud_theme.get_theme_by_id(package_doc.coverLetterTemplateId)

    if not resume_theme_doc or not cover_letter_theme_doc:
        raise HTTPException(status_code=404, detail="Component theme not found for this package")

    return ThemePackageWithTemplates(
        id=str(package_doc.id),
        name=package_doc.name,
        description=package_doc.description,
        resumeTemplate=ThemeTemplate(template=resume_theme_doc.template, styles=resume_theme_doc.styles),
        coverLetterTemplate=ThemeTemplate(template=cover_letter_theme_doc.template, styles=cover_letter_theme_doc.styles),
    )


@router.post("/render-pdfs")
async def render_pdfs(
    resume_id: str = Body(..., embed=True),
    cover_letter_id: str = Body(..., embed=True),
    theme_package_id: Optional[str] = Body(None, embed=True),
    use_example_theme: bool = Body(False, embed=True),
    upload: bool = Body(True, embed=True),
):
    """Generate PDFs for a stored resume + cover letter using a ThemePackage or example theme.

    Args:
        resume_id: ID of the resume to render
        cover_letter_id: ID of the cover letter to render
        theme_package_id: Optional ID of theme package to use (ignored if use_example_theme=True)
        use_example_theme: If True, uses the reference example theme with proper proportions
        upload: Whether to upload PDFs to Cloudinary

    Returns local file paths and (optionally) uploaded Cloudinary URLs.
    
    Example usage with example theme:
        {
            "resume_id": "507f1f77bcf86cd799439011",
            "cover_letter_id": "507f191e810c19729de860ea",
            "use_example_theme": true,
            "upload": true
        }
    """
    # 1. Fetch resume & cover letter (Beanie Documents)
    resume_doc = await ResumeResponse.find_one({"_id": ObjectId(resume_id)})
    if not resume_doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    cover_doc = await CoverLetterFull.find_one({"_id": cover_letter_id})
    if not cover_doc:
        raise HTTPException(status_code=404, detail="Cover letter not found")

    # 2. Determine which theme to use
    if use_example_theme:
        # Use the reference example theme
        theme_schema = get_example_theme()
    else:
        # Use a stored theme package (original behavior)
        if not theme_package_id:
            raise HTTPException(
                status_code=400, 
                detail="Either theme_package_id must be provided or use_example_theme must be true"
            )
        
        package = await crud_theme.get_theme_package_by_id(theme_package_id)
        if not package:
            raise HTTPException(status_code=404, detail="Theme package not found")
        resume_theme = await crud_theme.get_theme_by_id(
            package.resumeTemplateId if hasattr(package, 'resumeTemplateId') else package.resume_template_id
        )
        cover_theme = await crud_theme.get_theme_by_id(
            package.coverLetterTemplateId if hasattr(package, 'coverLetterTemplateId') else package.cover_letter_template_id
        )
        if not resume_theme or not cover_theme:
            raise HTTPException(status_code=400, detail="Theme package has invalid component theme IDs")

        # Build ThemeSchema (aggregate)
        theme_schema = ThemeSchema(
            name=package.name,
            description=package.description,
            resume_template=ThemeTemplate(template=resume_theme.template, styles=resume_theme.styles),
            cover_letter_template=ThemeTemplate(template=cover_theme.template, styles=cover_theme.styles),
        )

    # 3. Render + upload
    result = create_designed_pdfs(
        resume_obj=resume_doc.model_dump(),
        cover_letter_obj=cover_doc.model_dump(),
        theme=theme_schema,
        upload=upload,
    )
    
    return {
        "status": 200, 
        "message": "PDFs generated" + (" using example theme" if use_example_theme else ""),
        "data": result
    }


@router.post("/triage/{theme_id}", response_model=ThemeTriageResponse)
async def triage_theme(
    theme_id: str,
    *,
    resume_pdf: Optional[UploadFile] = File(default=None),
    cover_letter_pdf: Optional[UploadFile] = File(default=None),
    max_retries: int = Form(default=1, ge=0, le=3)
):
    """
    Intelligent theme triage and repair workflow.
    
    Uploads a resume and/or cover letter PDF with visual/layout issues, and the system:
    1. Analyzes the PDF(s) to identify problems
    2. Maps issues to theme code locations
    3. Generates fixes for all identified issues
    4. Updates the theme in the database
    5. Renders new PDFs to verify fixes
    6. Optionally retries if issues remain
    
    Args:
        theme_id: ID of the theme package to analyze and fix
        resume_pdf: Optional resume PDF with issues (at least one PDF required)
        cover_letter_pdf: Optional cover letter PDF with issues (at least one PDF required)
        max_retries: Number of retry attempts if verification fails (0-3, default 1)
    
    Returns:
        Summary of issues found, fixes applied, and verification results
    
    Example usage:
        curl -X POST "http://localhost:8000/api/v1/themes/triage/THEME_ID" \
          -F "resume_pdf=@problem_resume.pdf" \
          -F "max_retries=2"
    """
    
    try:
        # Handle FastAPI quirk where empty file fields come as empty strings or have empty filenames
        # This happens when the form field is present but no file is actually uploaded
        if resume_pdf:
            if not hasattr(resume_pdf, 'filename') or not resume_pdf.filename or resume_pdf.filename == "":
                resume_pdf = None
        if cover_letter_pdf:
            if not hasattr(cover_letter_pdf, 'filename') or not cover_letter_pdf.filename or cover_letter_pdf.filename == "":
                cover_letter_pdf = None
            
        # Validate that at least one PDF is provided
        if not resume_pdf and not cover_letter_pdf:
            raise HTTPException(
                status_code=400,
                detail="At least one PDF (resume_pdf or cover_letter_pdf) must be provided"
            )
        
        # Execute the workflow
        result = await execute_theme_triage_workflow(
            theme_id=theme_id,
            resume_pdf=resume_pdf,
            cover_letter_pdf=cover_letter_pdf,
            max_retries=max_retries
        )
        
        # Build response
        return {
            "status": 200 if result["success"] else 206,  # 206 = Partial Content (fixes attempted but not verified)
            "message": (
                f"Theme triage completed successfully in {result['attempts']} attempt(s)"
                if result["success"]
                else f"Theme triage completed with issues remaining after {result['attempts']} attempt(s)"
            ),
            "data": result
        }
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Theme triage failed: {str(e)}")
