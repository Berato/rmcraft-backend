from typing import Dict, Any
from app.schemas.theme import ThemeSchema, ThemeTemplate
from app.schemas.theme_documents import ThemeDoc, ThemePackageDoc
from app.tools.serializers import serialize_document


def validate_and_build_theme_payload(final_response: Dict[str, Any]) -> ThemeSchema:
    """Validate aggregated agent outputs and construct a ThemeSchema.

    Expected structure:
        {
          'theme_brief': { name, description, ... },
          'resume_theme': { template, styles },
          'cover_letter_theme': { template, styles }
        }
    """
    required_top = ["theme_brief", "resume_theme", "cover_letter_theme"]
    missing = [k for k in required_top if k not in final_response or not final_response[k]]
    if missing:
        raise ValueError(f"Missing required agent outputs: {missing}")

    brief = final_response["theme_brief"]
    resume_theme = final_response["resume_theme"]
    cover_theme = final_response["cover_letter_theme"]

    for key in ["template", "styles"]:
        if key not in resume_theme:
            raise ValueError(f"resume_theme missing '{key}'")
        if key not in cover_theme:
            raise ValueError(f"cover_letter_theme missing '{key}'")

    # Construct schema (ignore extra brief keys)
    schema = ThemeSchema(
        name=brief.get("name", "Untitled Theme"),
        description=brief.get("description"),
        resume_template=ThemeTemplate(template=resume_theme["template"], styles=resume_theme["styles"]),
        cover_letter_template=ThemeTemplate(template=cover_theme["template"], styles=cover_theme["styles"]),
    )
    return schema

async def save_theme_from_agents(final_response: Dict[str, Any]) -> Dict[str, Any]:
    """Validate agent JSON output and persist resume + cover letter themes + package using Beanie Documents.

    Returns the saved ThemePackageDoc.
    """
    theme_schema = validate_and_build_theme_payload(final_response)

    # Create resume theme doc
    resume_doc = ThemeDoc(
        name=f"{theme_schema.name} - Resume",
        description=theme_schema.description or "",
        type="RESUME",
        template=theme_schema.resume_template.template,
        styles=theme_schema.resume_template.styles,
    )
    await resume_doc.insert()

    # Create cover letter theme doc
    cover_doc = ThemeDoc(
        name=f"{theme_schema.name} - Cover Letter",
        description=theme_schema.description or "",
        type="COVER_LETTER",
        template=theme_schema.cover_letter_template.template,
        styles=theme_schema.cover_letter_template.styles,
    )
    await cover_doc.insert()

    # Create package
    package_doc = ThemePackageDoc(
        name=theme_schema.name,
        description=theme_schema.description or "",
        resumeTemplateId=str(resume_doc.id),
        coverLetterTemplateId=str(cover_doc.id),
    )
    await package_doc.insert()
    # Return a JSON-friendly dict (convert ObjectId/datetimes) to avoid FastAPI response-model
    # validation issues when returning raw Document objects.
    return serialize_document(package_doc)

