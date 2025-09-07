from fastapi import APIRouter, Body, UploadFile, File, status, HTTPException
from app.features.theme_generator import create_and_save_theme
from app.schemas.ResumeSchemas import ThemePackage, ResumeResponse  # Import actual schemas
from app.schemas.CoverLetterSchemas import CoverLetterFull
from typing import List, Optional
from app.crud import crud_theme
from app.services.designer_pdf import create_designed_pdfs
from app.schemas.theme import ThemeSchema, ThemeTemplate, ThemePackageWithTemplates
from app.schemas.theme_documents import ThemeDoc, ThemePackageDoc
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
    theme_package_id: str = Body(..., embed=True),
    resume_id: str = Body(..., embed=True),
    cover_letter_id: str = Body(..., embed=True),
    upload: bool = Body(True, embed=True),
):
    """Generate PDFs for a stored resume + cover letter using a ThemePackage.

    Returns local file paths and (optionally) uploaded Cloudinary URLs.
    """
    # 1. Fetch ThemePackage + component themes
    package = await crud_theme.get_theme_package_by_id(theme_package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Theme package not found")
    resume_theme = await crud_theme.get_theme_by_id(package.resumeTemplateId if hasattr(package, 'resumeTemplateId') else package.resume_template_id)
    cover_theme = await crud_theme.get_theme_by_id(package.coverLetterTemplateId if hasattr(package, 'coverLetterTemplateId') else package.cover_letter_template_id)
    if not resume_theme or not cover_theme:
        raise HTTPException(status_code=400, detail="Theme package has invalid component theme IDs")

    # 2. Fetch resume & cover letter (Beanie Documents)
    resume_doc = await ResumeResponse.find_one({"_id": resume_id})
    if not resume_doc:
        raise HTTPException(status_code=404, detail="Resume not found")
    cover_doc = await CoverLetterFull.find_one({"_id": cover_letter_id})
    if not cover_doc:
        raise HTTPException(status_code=404, detail="Cover letter not found")

    # 3. Build ThemeSchema (aggregate)
    theme_schema = ThemeSchema(
        name=package.name,
        description=package.description,
        resume_template=ThemeTemplate(template=resume_theme.template, styles=resume_theme.styles),
        cover_letter_template=ThemeTemplate(template=cover_theme.template, styles=cover_theme.styles),
    )

    # 4. Render + upload
    result = create_designed_pdfs(
        resume_obj=resume_doc.model_dump(),
        cover_letter_obj=cover_doc.model_dump(),
        theme=theme_schema,
        upload=upload,
    )
    return {"status": 200, "message": "PDFs generated", "data": result}
