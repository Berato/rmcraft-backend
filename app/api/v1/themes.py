from fastapi import APIRouter, Body, UploadFile, File, status
from app.features.theme_generator import create_and_save_theme
from app.schemas.ResumeSchemas import ThemePackage # Import your actual schema

router = APIRouter(prefix="/themes", tags=["Themes"])

@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=ThemePackage)
async def create_theme_endpoint(
    design_prompt: str = Body(..., embed=True),
    inspiration_image: UploadFile = File(...)
):
    """
    Agentically generates and saves a new resume and cover letter theme
    based on a text prompt and an inspiration image.
    """
    image_data = await inspiration_image.read()
    image_mime_type = inspiration_image.content_type
    
    # The orchestrator runs the full workflow and returns an object matching the ThemePackage schema
    saved_theme = await create_and_save_theme(
        design_prompt=design_prompt, 
        image_data=image_data, 
        image_mime_type=image_mime_type
    )
    
    return saved_theme
