from fastapi import APIRouter, Body, UploadFile, File, status, Depends, HTTPException
from app.features.theme_generator import create_and_save_theme
from app.schemas.ResumeSchemas import ThemePackage # Import your actual schema
from typing import List, Optional
from sqlalchemy.orm import Session
from app.crud import crud_theme
from app.db.session import get_db
import uuid

router = APIRouter(prefix="/themes", tags=["Themes"])

@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=ThemePackage)
async def create_theme_endpoint(
    design_prompt: str = Body(..., embed=True),
    inspiration_image: UploadFile = File(...),
    user_id: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db)
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
        db=db
    )
    
    return saved_theme

@router.get("/", response_model=List[ThemePackage])
def read_themes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Retrieve a list of theme packages.
    """
    themes = crud_theme.get_theme_packages(db, skip=skip, limit=limit)
    return themes

@router.get("/{theme_package_id}", response_model=ThemePackage)
def read_theme_package(theme_package_id: str, db: Session = Depends(get_db)):
    """
    Retrieve a specific theme package by ID.
    """
    theme_package = crud_theme.get_theme_package_by_id(db, theme_package_id)
    if theme_package is None:
        raise HTTPException(status_code=404, detail="Theme package not found")
    return theme_package
