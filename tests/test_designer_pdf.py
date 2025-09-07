from app.services.designer_pdf import minimal_theme_for_testing, create_designed_pdfs
import os


def test_create_designed_pdfs(tmp_path):
    theme = minimal_theme_for_testing()
    resume_obj = {
        "personalInfo": {"firstName": "Jane", "lastName": "Doe"},
        "experience": [
            {"position": "Engineer", "company": "Acme"},
        ],
        "summary": "Test summary",
    }
    cover_obj = {"title": "Cover Letter", "bodyParagraphs": ["Para 1", "Para 2"]}

    result = create_designed_pdfs(
        resume_obj=resume_obj,
        cover_letter_obj=cover_obj,
        theme=theme,
        output_dir=str(tmp_path),
        upload=False,
    )

    assert os.path.exists(result["resume_pdf_path"]) and result["resume_pdf_path"].endswith('.pdf')
    assert os.path.exists(result["cover_pdf_path"]) and result["cover_pdf_path"].endswith('.pdf')
    # No uploads requested
    assert result["resume_url"] is None
    assert result["cover_url"] is None
