import pytest
from app.services.theme_service import validate_and_build_theme_payload


def test_validate_and_build_theme_payload_success():
    final_response = {
        "theme_brief": {"name": "Modern Blue", "description": "Clean."},
        "resume_theme": {"template": "<h1>{{ resume.name }}</h1>", "styles": "h1{color:blue;}"},
        "cover_letter_theme": {"template": "<h1>{{ cover_letter.title }}</h1>", "styles": "h1{color:blue;}"},
    }
    schema = validate_and_build_theme_payload(final_response)
    assert schema.name == "Modern Blue"
    assert "resume_template" in schema.model_dump()


def test_validate_and_build_theme_payload_missing():
    with pytest.raises(ValueError):
        validate_and_build_theme_payload({"resume_theme": {}, "cover_letter_theme": {}})


def test_validate_and_build_theme_payload_missing_keys():
    with pytest.raises(ValueError):
        validate_and_build_theme_payload(
            {
                "theme_brief": {"name": "X"},
                "resume_theme": {"template": "abc"},  # missing styles
                "cover_letter_theme": {"template": "abc", "styles": ""},
            }
        )
