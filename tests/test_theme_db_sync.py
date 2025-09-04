import pytest
import asyncio
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import UniqueConstraint

from app.models.theme import Theme, ThemePackage


def test_theme_model_includes_preview_image_and_unique_name():
    cols = Theme.__table__.columns.keys()
    assert 'previewImageUrl' in cols, "Theme.previewImageUrl column missing"
    assert Theme.__table__.columns['name'].unique is True, "Theme.name should be unique"


def test_theme_package_column_names_and_indexes():
    cols = ThemePackage.__table__.columns.keys()
    assert 'resumeTemplateId' in cols, "ThemePackage.resumeTemplateId column missing"
    assert 'coverLetterTemplateId' in cols, "ThemePackage.coverLetterTemplateId column missing"

    # Verify unique constraint on the pair
    uniques = [c for c in ThemePackage.__table__.constraints if isinstance(c, UniqueConstraint)]
    assert any(
        {col.name for col in uc.columns} == {"resumeTemplateId", "coverLetterTemplateId"}
        for uc in uniques
    ), "Unique constraint on (resumeTemplateId, coverLetterTemplateId) missing"


def test_insert_compiles_with_camelcase_columns():
    stmt = ThemePackage.__table__.insert().values(
        id='pk',
        name='Basic Package',
        description='desc',
        resumeTemplateId='res-id',
        coverLetterTemplateId='cov-id'
    )
    compiled = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert '"resumeTemplateId"' in compiled
    assert '"coverLetterTemplateId"' in compiled


class _FakeQuery:
    def filter(self, *args, **kwargs):
        return self
    def first(self):
        return None

class _FakeSession:
    def query(self, *args, **kwargs):
        return _FakeQuery()


@pytest.mark.asyncio
async def test_service_create_theme_package_validates_fk():
    from app.services.theme_service import create_theme_package
    fake_db = _FakeSession()
    with pytest.raises(ValueError):
        # Missing referenced Theme rows should raise
        await create_theme_package(
            db=fake_db,
            name="pkg",
            description="desc",
            resume_template_id="res-id",
            cover_letter_template_id="cov-id",
        )
