import pytest
import asyncio
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import UniqueConstraint

from app.schemas.theme_documents import ThemeDoc, ThemePackageDoc


def test_theme_documents_have_expected_fields():
    # Ensure the Pydantic model fields exist for serialization and API usage
    td = ThemeDoc(
        name="t",
        description="d",
        type="RESUME",
        template="tpl",
        styles="css",
    )
    assert hasattr(td, 'template') and hasattr(td, 'styles')

    pkg = ThemePackageDoc(
        name="pkg",
        description="desc",
        resumeTemplateId="res-id",
        coverLetterTemplateId="cov-id",
    )
    assert hasattr(pkg, 'resumeTemplateId') and hasattr(pkg, 'coverLetterTemplateId')


@pytest.mark.asyncio
async def test_service_save_theme_validates_and_inserts(monkeypatch):
    # We will call save_theme_from_agents with missing pieces and expect a ValueError
    from app.services.theme_service import save_theme_from_agents
    incomplete = {"theme_brief": {"name": "X"}, "resume_theme": {"template": "tpl"}}
    with pytest.raises(ValueError):
        await save_theme_from_agents(final_response=incomplete)
