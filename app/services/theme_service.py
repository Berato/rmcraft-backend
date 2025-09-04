from sqlalchemy.orm import Session
from app.models.theme import Theme, ThemeType, ThemePackage
from app.db.session import get_db
from sqlalchemy.exc import IntegrityError

async def create_theme(
    db: Session,
    name: str,
    description: str,
    type: ThemeType,
    template: str,
    styles: str
) -> Theme:
    """
    Create a new theme in the database.

    Args:
        db: Database session
        name: Theme name
        description: Theme description
        type: Theme type (RESUME or COVER_LETTER)
        template: Jinja2 template string
        styles: CSS styles string

    Returns:
        Created Theme object
    """
    theme = Theme(
        name=name,
        description=description,
        type=type,
        template=template,
        styles=styles
    )
    db.add(theme)
    db.commit()
    db.refresh(theme)
    return theme

async def create_theme_package(
    db: Session,
    name: str,
    description: str,
    resume_template_id: str,
    cover_letter_template_id: str
) -> ThemePackage:
    """
    Create a new theme package linking resume and cover letter themes.

    Args:
        db: Database session
        name: Package name
        description: Package description
        resume_template_id: ID of the resume theme
        cover_letter_template_id: ID of the cover letter theme

    Returns:
        Created ThemePackage object
    """
    # Validate referenced themes exist (FK RESTRICT)
    resume_theme = db.query(Theme).filter(Theme.id == resume_template_id).first()
    cover_theme = db.query(Theme).filter(Theme.id == cover_letter_template_id).first()
    if not resume_theme or not cover_theme:
        raise ValueError("Referenced Theme IDs must exist (FK RESTRICT)")

    package = ThemePackage(
        name=name,
        description=description,
        resume_template_id=resume_template_id,
        cover_letter_template_id=cover_letter_template_id
    )
    db.add(package)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        # Likely unique pair violation or FK issue
        raise e
    db.refresh(package)
    return package
